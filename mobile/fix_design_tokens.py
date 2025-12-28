import re

with open('lib/core/design/design_tokens.dart', 'r') as f:
    content = f.read()

# Replace all DS.brandPrimary with the actual color
content = re.sub(r'DS\.brandPrimary', 'Color(0xFFFF6B35)', content)
content = re.sub(r'DS\.brandSecondary', 'Color(0xFF1A237E)', content)
content = re.sub(r'DS\.success', 'Color(0xFF4CAF50)', content)

# Fix the overlay colors to use primaryBase instead
content = re.sub(r'Color\(0xFFFF6B35\)\.withValues', 'primaryBase.withValues', content)

with open('lib/core/design/design_tokens.dart', 'w') as f:
    f.write(content)

print("Fixed design_tokens.dart")
