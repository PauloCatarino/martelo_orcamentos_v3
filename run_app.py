"""Ponto de entrada do executavel (PyInstaller).

Mantido separado de app/main.py para o empacotamento: o PyInstaller aponta
para este ficheiro, que arranca a aplicacao normal.
"""

import sys

from app.main import main

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == '--diagnostico-ia':
        import json
        from pathlib import Path
        from app.config.versao import APP_VERSION
        result = {'version': APP_VERSION}
        try:
            import torch
            import scipy.stats
            import sklearn
            import transformers
            from sentence_transformers import SentenceTransformer
            result.update(ok=True, torch=torch.__version__, transformers=transformers.__version__,
                          tensor_sum=torch.tensor([1, 2]).sum().item())
        except Exception as exc:
            result.update(ok=False, error=f'{type(exc).__name__}: {exc}')
        Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        sys.exit(0 if result['ok'] else 1)
    sys.exit(main())
