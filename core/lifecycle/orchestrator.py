import asyncio
import inspect
import logging
from typing import List, Dict, Set
from .registry import ComponentRegistry
from .health import HealthMonitor
from .models import ComponentRegistration, StartupReport, ShutdownReport
from .states import ComponentState
from .exceptions import StartupError, ShutdownError
from .interfaces import Bootable, Startable, Stoppable, DisposableComponent

logger = logging.getLogger(__name__)


class LifecycleOrchestrator:
    """
    Executes lifecycle transitions for registered components.
    Determines execution order using a dependency DAG (Topological Sort).
    """
    def __init__(self, registry: ComponentRegistry, health: HealthMonitor):
        self._registry = registry
        self._health = health

    def _build_execution_order(self) -> List[ComponentRegistration]:
        """
        Builds the startup sequence using topological sort on dependencies.
        Ties are broken by priority (lower priority number starts earlier).
        Raises StartupError on circular dependencies.
        """
        components = self._registry.get_all()
        
        # Build dependency graph
        graph: Dict[str, List[str]] = {comp.name: [] for comp in components}
        in_degree: Dict[str, int] = {comp.name: 0 for comp in components}
        
        for comp in components:
            for dep in comp.dependencies:
                if dep not in graph:
                    raise StartupError(f"Component '{comp.name}' depends on unknown component '{dep}'")
                graph[dep].append(comp.name)
                in_degree[comp.name] += 1
                
        # Use a list sorted by priority for the zero in-degree nodes to break ties
        # Lower priority number = starts first
        zero_in_degree = [comp for comp in components if in_degree[comp.name] == 0]
        zero_in_degree.sort(key=lambda c: (c.priority, c.name))
        
        execution_order: List[ComponentRegistration] = []
        
        while zero_in_degree:
            current = zero_in_degree.pop(0)
            execution_order.append(current)
            
            # Sort neighbors to ensure deterministic ordering by priority
            neighbors = [self._registry.get(n) for n in graph[current.name]]
            neighbors.sort(key=lambda c: (c.priority, c.name))
            
            for neighbor in neighbors:
                in_degree[neighbor.name] -= 1
                if in_degree[neighbor.name] == 0:
                    zero_in_degree.append(neighbor)
                    # Re-sort to maintain priority order
                    zero_in_degree.sort(key=lambda c: (c.priority, c.name))
                    
        if len(execution_order) != len(components):
            raise StartupError("Circular dependency detected in component registration")
            
        return execution_order

    async def _execute_hook(self, component: ComponentRegistration, hook_name: str) -> None:
        """Executes a specific lifecycle hook if it exists on the instance, with timeout."""
        if hasattr(component.instance, hook_name) and callable(getattr(component.instance, hook_name)):
            hook = getattr(component.instance, hook_name)
            if inspect.iscoroutinefunction(hook):
                timeout = None
                if 'boot' in hook_name or 'start' in hook_name:
                    timeout = component.startup_timeout
                elif 'stop' in hook_name or 'shutdown' in hook_name:
                    timeout = component.shutdown_timeout
                
                try:
                    if timeout:
                        await asyncio.wait_for(hook(), timeout=timeout)
                    else:
                        await hook()
                except asyncio.TimeoutError:
                    msg = f"Component '{component.name}' timed out during '{hook_name}'."
                    raise TimeoutError(msg)
            else:
                raise TypeError(f"Lifecycle hook '{hook_name}' on '{component.name}' must be an async function.")

    async def boot(self) -> StartupReport:
        return await self._run_startup_phase("boot", "before_boot", "boot", "after_boot", ComponentState.BOOTING, ComponentState.BOOTED)

    async def start(self) -> StartupReport:
        return await self._run_startup_phase("start", "before_start", "start", "after_start", ComponentState.STARTING, ComponentState.RUNNING)

    async def _run_startup_phase(self, phase_name: str, before_hook: str, action_hook: str, after_hook: str, 
                                 in_progress_state: ComponentState, success_state: ComponentState) -> StartupReport:
        try:
            execution_order = self._build_execution_order()
        except StartupError as e:
            return StartupReport(success=False, started_components=[], error_details=str(e))

        started = []
        for comp in execution_order:
            if not comp.enabled:
                continue
                
            self._health._update_state(comp.name, in_progress_state)
            try:
                await self._execute_hook(comp, before_hook)
                await self._execute_hook(comp, action_hook)
                await self._execute_hook(comp, after_hook)
                
                self._health._update_state(comp.name, success_state)
                started.append(comp.name)
            except Exception as e:
                self._health.failed(comp.name, str(e))
                logger.error(f"Failed to {phase_name} component '{comp.name}': {e}")
                
                if comp.critical:
                    # Rollback already started components in this phase
                    # This relies on the shutdown/stop pipeline which goes in reverse order
                    await self._rollback(started, phase_name)
                    return StartupReport(
                        success=False, 
                        started_components=started, 
                        failed_component=comp.name, 
                        error_details=str(e)
                    )
                else:
                    logger.warning(f"Component '{comp.name}' is not critical. Continuing startup.")
                    
        return StartupReport(success=True, started_components=started)

    async def _rollback(self, started_components: List[str], phase_name: str) -> None:
        """Rolls back already started components in reverse order."""
        # Reverse the list to stop newest first
        for name in reversed(started_components):
            comp = self._registry.get(name)
            if not comp:
                continue
            
            try:
                if phase_name == "start":
                    self._health.shutting_down(name, "Rolling back start")
                    await self._execute_hook(comp, "before_stop")
                    await self._execute_hook(comp, "stop")
                    await self._execute_hook(comp, "after_stop")
                    self._health.stopped(name)
                elif phase_name == "boot":
                    self._health.shutting_down(name, "Rolling back boot")
                    await self._execute_hook(comp, "before_shutdown")
                    await self._execute_hook(comp, "shutdown")
                    await self._execute_hook(comp, "after_shutdown")
                    self._health.stopped(name)
            except Exception as e:
                logger.error(f"Failed to rollback component '{name}': {e}")
                self._health.failed(name, f"Rollback failed: {e}")

    async def stop(self) -> ShutdownReport:
        return await self._run_shutdown_phase("stop", "before_stop", "stop", "after_stop", ComponentState.STOPPING, ComponentState.STOPPED)

    async def shutdown(self) -> ShutdownReport:
        return await self._run_shutdown_phase("shutdown", "before_shutdown", "shutdown", "after_shutdown", ComponentState.SHUTTING_DOWN, ComponentState.STOPPED)

    async def _run_shutdown_phase(self, phase_name: str, before_hook: str, action_hook: str, after_hook: str,
                                  in_progress_state: ComponentState, success_state: ComponentState) -> ShutdownReport:
        try:
            execution_order = self._build_execution_order()
        except StartupError as e:
            # If graph is broken, we'll just try to shut down everything we can find, perhaps in reverse priority order
            logger.warning(f"Dependency graph is broken during {phase_name}: {e}. Falling back to reverse priority shutdown.")
            execution_order = self._registry.get_all()
            execution_order.sort(key=lambda c: (c.priority, c.name))
            
        # Shutdown is the reverse of startup execution order
        shutdown_order = list(reversed(execution_order))
        
        stopped = []
        errors = {}
        
        for comp in shutdown_order:
            if not comp.enabled:
                continue
                
            self._health._update_state(comp.name, in_progress_state)
            try:
                await self._execute_hook(comp, before_hook)
                await self._execute_hook(comp, action_hook)
                await self._execute_hook(comp, after_hook)
                
                self._health._update_state(comp.name, success_state)
                stopped.append(comp.name)
            except Exception as e:
                self._health.failed(comp.name, f"Failed to {phase_name}: {e}")
                errors[comp.name] = str(e)
                logger.error(f"Error during {phase_name} of '{comp.name}': {e}")
                # We continue shutting down other components even if one fails
                
        return ShutdownReport(success=len(errors) == 0, stopped_components=stopped, errors=errors)

    async def restart(self) -> bool:
        """Restarts the system by stopping and then starting."""
        shutdown_report = await self.stop()
        if not shutdown_report.success:
            logger.error("Failed to stop all components during restart.")
            return False
            
        startup_report = await self.start()
        return startup_report.success
