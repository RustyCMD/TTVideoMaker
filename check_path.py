import sys
import site

print("sys.path:")
for p in sys.path:
    print(p)

print("\nUser site-packages:")
print(site.USER_SITE) 