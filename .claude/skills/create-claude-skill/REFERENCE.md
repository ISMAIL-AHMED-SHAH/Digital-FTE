# Efficient Skill Reference

## Token Optimization

### Data Filtering
```python
# Filter in script, return minimal output
data = get_large_dataset()  # 10,000 rows
filtered = [r for r in data if r.status == 'active'][:5]
print(f"✓ {len(filtered)} active items")
```

### Client-Side Processing
```python
def process(raw_data):
    result = complex_calculation(raw_data)
    return f"✓ Processed: {result.summary}"
```

## Script Patterns

### Standard Template
```python
#!/usr/bin/env python3
import subprocess, json, sys

def main():
    try:
        result = subprocess.run(
            ['command', 'args'],
            capture_output=True, text=True, check=True
        )
        data = json.loads(result.stdout)
        
        # Process locally
        summary = process(data)
        
        print(f"✓ {summary}")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"✗ Command failed: {e.stderr.strip()}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### With Arguments
```python
#!/usr/bin/env python3
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: script.py <arg>")
        sys.exit(1)
    
    arg = sys.argv[1]
    # ... operation
    print(f"✓ Done with {arg}")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

## Output Format

### Success
```
✓ Operation completed
✓ 5 items processed
✓ All checks passed
```

### Failure
```
✗ Operation failed: reason
✗ 3/5 checks failed
✗ Error: description
```

## Environment Variables

```python
import os

api_key = os.environ.get('API_KEY')
if not api_key:
    print("✗ API_KEY not set")
    sys.exit(1)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Permission denied | `chmod +x scripts/*.py` |
| Module not found | Check virtual environment or install deps |
| Path issues | Use `os.path.dirname(os.path.abspath(__file__))` |
| Large output | Limit with `str(result)[:1000]` |
