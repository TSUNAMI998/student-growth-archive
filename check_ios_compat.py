import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract JS between <script> tags
scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
js = scripts[-1] if scripts else ''

print(f'File size: {len(content)} bytes')
print(f'JS length: {len(js)} chars')

# Check for potential iOS issues
features = {
    'template literals': '${' in js,
    'const/let': 'const ' in js or 'let ' in js,
    'arrow functions': '=>' in js,
    'for..of': 'for (const ' in js or 'for (let ' in js,
    'destructuring': 'const {' in js or 'const [' in js,
    'includes()': '.includes(' in js,
    'find()': '.find(' in js,
    'findIndex()': '.findIndex(' in js,
}

print('\n=== JS Features Used ===')
for feat, used in features.items():
    print(f'  [{"YES" if used else "NO"}] {feat}')

# iOS Safari compatibility
print('\n=== iOS Safari Compatibility ===')
print('  iOS 9 (Safari 9): Does NOT support const/let, arrow, template literals, for..of, includes, find, findIndex')
print('  iOS 10+ (Safari 10+): Supports all listed features')
print('  Current iPhones: 95%+ are on iOS 13+ (Safari 13+)')

# Check viewport meta
viewport_match = re.search(r'<meta name="viewport" content="([^"]+)"', content)
if viewport_match:
    print(f'\n  Viewport: {viewport_match.group(1)}')

# Check meta tags
print('\n=== Mobile Meta Tags ===')
if 'apple-mobile-web-app-capable' in content:
    print('  apple-mobile-web-app-capable: PRESENT')
else:
    print('  apple-mobile-web-app-capable: MISSING')
    
if 'apple-mobile-web-app-status-bar-style' in content:
    print('  apple-mobile-web-app-status-bar-style: PRESENT')
else:
    print('  apple-mobile-web-app-status-bar-style: MISSING')
    
if 'theme-color' in content:
    print('  theme-color: PRESENT')
else:
    print('  theme-color: MISSING')

# Check for CSS issues
print('\n=== CSS Checks ===')
if '-webkit-tap-highlight-color' in content:
    print('  -webkit-tap-highlight-color: PRESENT')
else:
    print('  -webkit-tap-highlight-color: MISSING')

if 'env(safe-area-inset-bottom)' in content or 'constant(safe-area-inset-bottom)' in content:
    print('  safe-area-inset: PRESENT')
else:
    print('  safe-area-inset: MISSING')

# Check for very long lines that might cause issues
long_lines = [i+1 for i, line in enumerate(content.split('\n')) if len(line) > 10000]
if long_lines:
    print(f'\nWARNING: {len(long_lines)} lines exceed 10,000 characters (might cause rendering issues)')
else:
    print('\nLine lengths: OK')
