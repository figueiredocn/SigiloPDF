"""Ponto de entrada Windows e validação explícita somente com dados sintéticos."""

import sys
from app.main import main


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--validar-build":
        from app.utils.build_validation import validate_build
        raise SystemExit(validate_build(sys.argv[2]))
    raise SystemExit(main())
