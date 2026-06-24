"""Read-only helpers for production process folders on the server."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.producao import Producao
from app.services.system_setting_service import SystemSettingService


DEFAULT_PASTA_ENCOMENDA = "Encomenda de Cliente"
DEFAULT_PASTA_ENCOMENDA_FINAL = "Encomenda de Cliente Final"
DEFAULT_BASE_PATH = r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep_Producao"
KEY_PRODUCAO_BASE_PATH = "producao_base_path"
MAX_NOS_ARVORE = 2000

PRODUCAO_BASE_PATH_KEY = KEY_PRODUCAO_BASE_PATH
PRODUCAO_BASE_PATH_DEFAULT = DEFAULT_BASE_PATH
TIPO_ENCOMENDA_CLIENTE = DEFAULT_PASTA_ENCOMENDA
TIPO_ENCOMENDA_CLIENTE_FINAL = DEFAULT_PASTA_ENCOMENDA_FINAL

ArvorePastasProcesso = dict[str, dict[str, list[str]]]


def _normalizar_path_windows(p) -> str:
    s = str(p or "").strip().strip('"').strip("'").replace("/", "\\")
    if not s:
        return ""
    is_unc = s.startswith("\\\\")
    s = re.sub(r"\\+", r"\\", s)
    if is_unc and not s.startswith("\\\\"):
        s = "\\" + s
    return s


def _two_digit(value: str | int | None) -> str:
    """Normaliza para 2 digitos (zero-fill)."""
    if value is None:
        return "01"
    text = str(value).strip()
    if text.isdigit():
        return f"{int(text):02d}"
    return text[:2] if len(text) >= 2 else text.zfill(2)


def _num_enc_norm(num_enc: str | int | None) -> str:
    """Normaliza numero de encomenda em 4 caracteres (PHC: 4 digitos | Cliente Final: _NNN)."""
    if num_enc is None:
        raise ValueError("Numero de encomenda PHC em falta.")
    text = str(num_enc).strip()
    if text.startswith("_"):
        m = re.fullmatch(r"_(\d{1,3})", text)
        if not m:
            raise ValueError("Numero de encomenda invalido.")
        return "_" + m.group(1).zfill(3)

    digits = re.sub(r"\D", "", text)
    if not digits:
        raise ValueError("Numero de encomenda PHC invalido.")
    if len(digits) < 4:
        digits = digits.zfill(4)
    return digits


def _ano_two_digits(ano: str | int | None) -> tuple[str, str]:
    """
    Retorna (ano_completo, ano_2d). Aceita '2025' ou '25'.
    Se None, usa ano atual.
    """
    import datetime as _dt

    if ano is None:
        ano_completo = str(_dt.datetime.now().year)
    else:
        ano_completo = str(ano).strip()
    if len(ano_completo) == 2:
        ano_2d = ano_completo
    else:
        try:
            ano_int = int(ano_completo)
            ano_2d = f"{ano_int % 100:02d}"
        except Exception:
            ano_2d = ano_completo[-2:]
    return ano_completo, ano_2d


def _producao_root_dir(
    session: Session,
    *,
    ano: str | int,
    tipo_pasta: Optional[str],
    base_dir: str | Path | None = None,
) -> Path:
    ano_full, _ = _ano_two_digits(ano)
    resolved_base = _resolve_base_dir(session, base_dir)
    tipo_dir = _pasta_tipo_dir(tipo_pasta)
    root = (
        f"{_normalizar_path_windows(resolved_base)}\\"
        f"{_normalizar_path_windows(ano_full)}\\"
        f"{_normalizar_path_windows(tipo_dir)}"
    )
    return Path(_normalizar_path_windows(root))


def _pasta_tipo_dir(tipo: str | None) -> str:
    if not tipo:
        return DEFAULT_PASTA_ENCOMENDA
    tipo_norm = str(tipo).strip().lower()
    if "final" in tipo_norm:
        return DEFAULT_PASTA_ENCOMENDA_FINAL
    return DEFAULT_PASTA_ENCOMENDA


def _clean_base_path(text: str) -> str:
    cleaned = str(text or "").strip().strip('"').strip("'")
    cleaned = cleaned.replace("/", "\\").replace("\r", "").replace("\n", "")
    if not cleaned:
        return ""
    is_unc = cleaned.startswith("\\\\")
    rest = cleaned[2:] if is_unc else cleaned
    while "\\\\" in rest:
        rest = rest.replace("\\\\", "\\")
    cleaned = ("\\\\" + rest) if is_unc else rest
    cleaned = cleaned.rstrip(" .").strip()
    if not cleaned:
        return ""
    # Caracteres proibidos em paths Windows (":" e permitido apenas em "C:\..." / "C:")
    invalid = re.search(r'[<>\"|?*]', cleaned)
    if invalid:
        raise ValueError(f"Caminho base de producao invalido (caractere {invalid.group(0)}).")
    if ":" in cleaned:
        # Aceita drive-letter: "C:\" ou "C:"
        if not re.match(r"^[A-Za-z]:($|\\)", cleaned):
            raise ValueError("Caminho base de producao invalido (caractere :).")
    return cleaned


def _resolve_base_dir(session: Session, base_dir: str | Path | None = None) -> str:
    """
    Decide o caminho base para producao, respeitando override do utilizador.
    Limpa aspas e barras sobrantes para evitar paths invalidos.
    """
    candidates = []
    if base_dir:
        candidates.append(str(base_dir))
    try:
        cfg_value = SystemSettingService(session).obter_valor(KEY_PRODUCAO_BASE_PATH, None)
        if cfg_value:
            candidates.append(cfg_value)
    except Exception:
        pass
    candidates.append(DEFAULT_BASE_PATH)
    for path_text in candidates:
        cleaned = _clean_base_path(path_text)
        if cleaned:
            return _normalizar_path_windows(cleaned)
    return _normalizar_path_windows(DEFAULT_BASE_PATH)


_FOLDER_PREFIX_SEPARATORS = ("_", "-", " ")
_SEP_PATTERN = r"(?:_|-| )"


def _folder_name_matches_prefix(name: str, prefix: str) -> bool:
    """
    Verifica se `name` corresponde ao `prefix`:
    - igual ao prefix, OU
    - comeca por prefix e o proximo char e um separador (ex.: '_' ou ' ').
    """
    name_text = str(name or "")
    prefix_text = str(prefix or "")
    if not name_text or not prefix_text:
        return False
    if not name_text.startswith(prefix_text):
        return False
    if len(name_text) == len(prefix_text):
        return True
    return name_text[len(prefix_text)] in _FOLDER_PREFIX_SEPARATORS


def listar_versoes_obra_em_pastas(
    session: Session,
    *,
    ano: str | int,
    num_enc_phc: str | int,
    tipo_pasta: Optional[str] = None,
    base_dir: str | Path | None = None,
) -> set[str]:
    """
    Lista versoes de obra (VV) existentes nas pastas do servidor para o mesmo ano+encomenda.
    Isto cobre casos onde as pastas existem (ex.: criadas por outros sistemas) mas ainda nao ha registo na BD.
    """
    enc = _num_enc_norm(num_enc_phc)
    root = _producao_root_dir(session, ano=ano, tipo_pasta=tipo_pasta, base_dir=base_dir)
    try:
        if not root.is_dir():
            return set()
    except Exception:
        return set()

    pat_vv = re.compile(rf"^{re.escape(enc)}{_SEP_PATTERN}(?P<vv>\d{{2}}){_SEP_PATTERN}", re.IGNORECASE)
    found: set[str] = set()

    try:
        for seg1 in root.iterdir():
            if not seg1.is_dir():
                continue
            if not _folder_name_matches_prefix(seg1.name, enc):
                continue
            try:
                for seg2 in seg1.iterdir():
                    if not seg2.is_dir():
                        continue
                    m = pat_vv.match(seg2.name)
                    if not m:
                        continue
                    found.add(_two_digit(m.group("vv")))
            except Exception:
                continue
    except Exception:
        return set()

    return found


def listar_versoes_plano_em_pastas(
    session: Session,
    *,
    ano: str | int,
    num_enc_phc: str | int,
    versao_obra: str | int,
    tipo_pasta: Optional[str] = None,
    base_dir: str | Path | None = None,
) -> set[str]:
    """
    Lista versoes de plano CUT-RITE (PP) existentes nas pastas do servidor dentro da versao de obra.
    """
    enc = _num_enc_norm(num_enc_phc)
    vv = _two_digit(versao_obra)
    root = _producao_root_dir(session, ano=ano, tipo_pasta=tipo_pasta, base_dir=base_dir)
    try:
        if not root.is_dir():
            return set()
    except Exception:
        return set()

    pat_vvpp = re.compile(
        rf"^{re.escape(enc)}{_SEP_PATTERN}{re.escape(vv)}{_SEP_PATTERN}(?P<pp>\d{{2}}){_SEP_PATTERN}",
        re.IGNORECASE,
    )
    found: set[str] = set()

    try:
        for seg1 in root.iterdir():
            if not seg1.is_dir():
                continue
            if not _folder_name_matches_prefix(seg1.name, enc):
                continue
            try:
                for seg2 in seg1.iterdir():
                    if not seg2.is_dir():
                        continue
                    if not _folder_name_matches_prefix(seg2.name, f"{enc}_{vv}"):
                        continue
                    try:
                        for seg3 in seg2.iterdir():
                            if not seg3.is_dir():
                                continue
                            m = pat_vvpp.match(seg3.name)
                            if not m:
                                continue
                            found.add(_two_digit(m.group("pp")))
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        return set()

    return found


def listar_pastas_enc_arvore(
    session: Session,
    *,
    ano: str | int,
    num_enc_phc: str | int,
    tipo_pasta: Optional[str] = None,
    base_dir: str | Path | None = None,
    max_nodes: int = 2000,
) -> tuple[str, dict[str, dict[str, list[str]]]]:
    """
    Devolve (root_path, arvore) das pastas existentes para uma encomenda.

    arvore: {seg1: {seg2: [seg3, ...]}}
    """
    enc = _num_enc_norm(num_enc_phc)
    root = _producao_root_dir(session, ano=ano, tipo_pasta=tipo_pasta, base_dir=base_dir)
    tree: dict[str, dict[str, list[str]]] = {}
    nodes = 0

    try:
        if not root.is_dir():
            return str(root), tree
    except Exception:
        return str(root), tree

    try:
        for seg1 in sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name.casefold()):
            if nodes >= max_nodes:
                break
            if not _folder_name_matches_prefix(seg1.name, enc):
                continue
            nodes += 1
            tree.setdefault(seg1.name, {})
            try:
                seg2_dirs = sorted((p for p in seg1.iterdir() if p.is_dir()), key=lambda p: p.name.casefold())
            except Exception:
                continue
            for seg2 in seg2_dirs:
                if nodes >= max_nodes:
                    break
                nodes += 1
                tree[seg1.name].setdefault(seg2.name, [])
                try:
                    seg3_dirs = sorted((p for p in seg2.iterdir() if p.is_dir()), key=lambda p: p.name.casefold())
                except Exception:
                    continue
                for seg3 in seg3_dirs:
                    if nodes >= max_nodes:
                        break
                    nodes += 1
                    tree[seg1.name][seg2.name].append(seg3.name)
    except Exception:
        pass

    return str(root), tree


def sugerir_proxima_versao_obra(
    session: Session,
    *,
    ano: str | int,
    num_enc_phc: str | int,
    tipo_pasta: Optional[str] = None,
    requested: str | int | None = None,
    base_dir: str | Path | None = None,
) -> str:
    """Sugere a proxima versao de obra (VV) nao usada para o mesmo ano+encomenda."""
    ano_full, _ = _ano_two_digits(ano)
    enc_norm = _num_enc_norm(num_enc_phc)
    existing = session.execute(
        select(Producao.versao_obra).where(
            Producao.ano == ano_full,
            Producao.num_enc_phc == enc_norm,
        )
    ).scalars().all()
    existing_set = {str(v or "").strip() for v in existing if str(v or "").strip()}
    try:
        existing_set |= set(
            listar_versoes_obra_em_pastas(
                session,
                ano=ano_full,
                num_enc_phc=enc_norm,
                tipo_pasta=tipo_pasta,
                base_dir=base_dir,
            )
        )
    except Exception:
        pass

    if requested is not None:
        req = _two_digit(requested)
        if req not in existing_set:
            return req

    parsed: list[int] = []
    for v in existing_set:
        try:
            parsed.append(int(v))
        except Exception:
            continue
    candidate = (max(parsed) + 1) if parsed else 1
    cand = _two_digit(candidate)
    while cand in existing_set:
        candidate += 1
        cand = _two_digit(candidate)
    return cand


def sugerir_proxima_versao_plano(
    session: Session,
    *,
    ano: str | int,
    num_enc_phc: str | int,
    versao_obra: str | int,
    tipo_pasta: Optional[str] = None,
    requested: str | int | None = None,
    base_dir: str | Path | None = None,
) -> str:
    """Sugere a proxima versao de plano CUT-RITE (PP) dentro da versao de obra."""
    ano_full, _ = _ano_two_digits(ano)
    enc_norm = _num_enc_norm(num_enc_phc)
    ver_obra = _two_digit(versao_obra)
    existing = session.execute(
        select(Producao.versao_plano).where(
            Producao.ano == ano_full,
            Producao.num_enc_phc == enc_norm,
            Producao.versao_obra == ver_obra,
        )
    ).scalars().all()
    existing_set = {str(v or "").strip() for v in existing if str(v or "").strip()}
    try:
        existing_set |= set(
            listar_versoes_plano_em_pastas(
                session,
                ano=ano_full,
                num_enc_phc=enc_norm,
                versao_obra=ver_obra,
                tipo_pasta=tipo_pasta,
                base_dir=base_dir,
            )
        )
    except Exception:
        pass

    if requested is not None:
        req = _two_digit(requested)
        if req not in existing_set:
            return req

    parsed: list[int] = []
    for v in existing_set:
        try:
            parsed.append(int(v))
        except Exception:
            continue
    candidate = (max(parsed) + 1) if parsed else 1
    cand = _two_digit(candidate)
    while cand in existing_set:
        candidate += 1
        cand = _two_digit(candidate)
    return cand


def _sanitize_folder_name(text: str) -> str:
    safe = re.sub(r"[\\/:*?\"<>|]", "_", text or "")
    return safe.strip() or "obra"


def _cliente_para_pasta(
    nome_simplex: Optional[str],
    nome_cliente: Optional[str],
    ref_cliente: Optional[str],
) -> str:
    return _sanitize_folder_name(nome_simplex or nome_cliente or ref_cliente or "cliente")


def segmentos_pasta(
    num_enc_phc: str | int,
    versao_obra: str | int,
    versao_plano: str | int,
    *,
    nome_simplex: Optional[str] = None,
    nome_cliente: Optional[str] = None,
    ref_cliente: Optional[str] = None,
) -> tuple[str, str, str]:
    enc = _num_enc_norm(num_enc_phc)
    ver_obra = _two_digit(versao_obra)
    ver_plano = _two_digit(versao_plano)
    cli = _cliente_para_pasta(nome_simplex, nome_cliente, ref_cliente)
    seg1 = f"{enc}_{cli}"
    seg2 = f"{enc}_{ver_obra}_{cli}"
    seg3 = f"{enc}_{ver_obra}_{ver_plano}_{cli}"
    return seg1, seg2, seg3


def caminho_versao(
    session: Session,
    *,
    ano: str | int,
    tipo_pasta: Optional[str],
    num_enc_phc: str | int,
    versao_obra: str | int,
    versao_plano: str | int,
    nome_simplex: Optional[str] = None,
    nome_cliente: Optional[str] = None,
    ref_cliente: Optional[str] = None,
) -> Path:
    root = _producao_root_dir(session, ano=ano, tipo_pasta=tipo_pasta)
    seg1, seg2, seg3 = segmentos_pasta(
        num_enc_phc,
        versao_obra,
        versao_plano,
        nome_simplex=nome_simplex,
        nome_cliente=nome_cliente,
        ref_cliente=ref_cliente,
    )
    path_text = (
        f"{_normalizar_path_windows(root)}\\"
        f"{_normalizar_path_windows(seg1)}\\"
        f"{_normalizar_path_windows(seg2)}\\"
        f"{_normalizar_path_windows(seg3)}"
    )
    return Path(_normalizar_path_windows(path_text))


def criar_pasta_versao(caminho: Path) -> Path:
    try:
        caminho.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OSError(f"Falha ao criar pasta de producao: {caminho} ({exc})") from exc
    return caminho


def resolver_base_dir(session: Session) -> str:
    """Return the configured production base directory, normalized."""
    return _resolve_base_dir(session, None)


def arvore_pastas_processo(
    session: Session,
    *,
    ano,
    num_enc_phc,
    tipo_pasta,
) -> tuple[str, ArvorePastasProcesso]:
    """Return the read-only folder tree for one production process."""
    prefix = _num_enc_norm(num_enc_phc)
    root_path, arvore = listar_pastas_enc_arvore(
        session,
        ano=ano,
        num_enc_phc=prefix,
        tipo_pasta=tipo_pasta,
        max_nodes=MAX_NOS_ARVORE,
    )
    return root_path, arvore


def _norm_enc(num_enc: str | int | None) -> str:
    return _num_enc_norm(num_enc)


def _tipo_dir(tipo_pasta: str | None) -> str:
    return _pasta_tipo_dir(tipo_pasta)
