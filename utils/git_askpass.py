import os
import sys

def main():
    prompt = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if "username" in prompt:
        val = os.environ.get("GIT_ASKPASS_USERNAME", "")
    else:
        val = os.environ.get("GIT_ASKPASS_TOKEN", "")
        
    sys.stdout.write(val + "\n")
    sys.stdout.flush()
    sys.exit(0)

if __name__ == "__main__":
    main()
