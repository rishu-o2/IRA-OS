import re

with open('tests/core/android/test_android.py', 'r') as f:
    content = f.read()

content = re.sub(r'version="[^"]+"', lambda m: m.group(0) + ', security_level=SecurityLevel.LOW', content)

if 'SecurityLevel' not in content:
    content = content.replace('CapabilityDescriptor,', 'CapabilityDescriptor,\n    SecurityLevel,')

with open('tests/core/android/test_android.py', 'w') as f:
    f.write(content)

print('Fixed tests')
