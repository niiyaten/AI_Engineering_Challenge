from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main() -> int:
    src, dst, password = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    sys.path.insert(0, "/usr/lib/python3/dist-packages")
    import uno  # type: ignore
    from com.sun.star.beans import PropertyValue  # type: ignore

    def prop(name, value):
        p = PropertyValue(); p.Name = name; p.Value = value; return p

    with tempfile.TemporaryDirectory(prefix="rag-lo-") as profile:
        port = 21000 + (abs(hash(str(src))) % 20000)
        proc = subprocess.Popen([
            "libreoffice", "--headless", "--nologo", "--nodefault",
            f"-env:UserInstallation={uno.systemPathToFileUrl(profile)}",
            f"--accept=socket,host=127.0.0.1,port={port};urp;StarOffice.ComponentContext",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            ctx0 = uno.getComponentContext()
            resolver = ctx0.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", ctx0)
            ctx = None
            for _ in range(100):
                try:
                    ctx = resolver.resolve(f"uno:socket,host=127.0.0.1,port={port};urp;StarOffice.ComponentContext")
                    break
                except Exception:
                    time.sleep(.15)
            if ctx is None:
                raise RuntimeError("LibreOffice bridge unavailable")
            desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
            doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(str(src.resolve())), "_blank", 0, (prop("Hidden", True), prop("ReadOnly", True), prop("Password", password)))
            if doc is None:
                raise RuntimeError("password rejected")
            filters = {".docx": "Office Open XML Text", ".xlsx": "Calc MS Excel 2007 XML", ".pptx": "Impress MS PowerPoint 2007 XML"}
            dst.parent.mkdir(parents=True, exist_ok=True)
            doc.storeAsURL(uno.systemPathToFileUrl(str(dst.resolve())), (prop("FilterName", filters[dst.suffix.lower()]), prop("Overwrite", True)))
            doc.close(True)
        finally:
            proc.terminate()
            try: proc.wait(timeout=5)
            except Exception: proc.kill()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
