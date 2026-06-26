"""
scraper_visualizar.py
Scrapes NFS-e data from the Visualizar page without downloading XML/PDF.
No captcha required - just page.goto() to the Visualizar URL.
"""

import re
import time

BASE_URL = "https://www.nfse.gov.br/EmissorNacional"

class SessionExpiredError(Exception):
    pass

def _wait_for_content(page, retries=5, delay=3):
    """Wait until the nota content is actually rendered on the page."""
    for attempt in range(retries):
        try:
            page.wait_for_load_state('networkidle', timeout=10000)
        except:
            pass
        time.sleep(1)
        els    = page.query_selector_all('span.form-control-static')
        filled = [e for e in els if (e.inner_text() or '').strip() not in ('', '-')]
        if len(filled) >= 3:
            return True
        print(f'[DEBUG] Attempt {attempt+1}/{retries}: {len(filled)} fields found, waiting {delay}s...', flush=True)
        time.sleep(delay)
    return False

def _get_panel_fields(panel):
    """Extract label->value pairs from a specific tab panel element."""
    fields = {}
    if not panel:
        return fields
    try:
        groups = panel.query_selector_all('.form-group')
        for group in groups:
            label_el = group.query_selector('label span') or group.query_selector('label')
            value_el = group.query_selector('span.form-control-static')
            if label_el and value_el:
                label = (label_el.inner_text() or '').strip().rstrip(':')
                value = re.sub(r'\s+', ' ', (value_el.inner_text() or '').strip())
                if label and value and value not in ('-', ''):
                    fields[label] = value
    except Exception as e:
        print(f'[DEBUG] _get_panel_fields error: {e}', flush=True)
    return fields

def _f(fields, *keys):
    """Get field value trying multiple possible label names."""
    for k in keys:
        if k in fields:
            return fields[k]
        for fk, fv in fields.items():
            if k.lower() in fk.lower():
                return fv
    return ''

def _to_float(s):
    if not s or s == '-':
        return 0.0
    try:
        s = re.sub(r'[R$\s]', '', s)
        return float(s.replace('.', '').replace(',', '.').strip())
    except:
        return 0.0

def scrape_visualizar(page, chave, retries=3):
    """
    Navigate to the Visualizar page for a nota and scrape all fields.
    Returns a dict with all fields, or None on failure.
    """
    url = f"{BASE_URL}/Notas/Visualizar/Index/{chave}"

    for attempt in range(retries):
        try:
            page.goto(url, timeout=30000)
            page.wait_for_load_state('domcontentloaded', timeout=15000)
            time.sleep(2)

            if 'Login' in page.url or 'login' in page.url.lower():
                raise SessionExpiredError(f"Sessão expirou ao acessar Visualizar {chave}")

            title = page.title()
            if '404' in title or '403' in title or 'Error' in title or 'Erro' in title:
                print(f'[AVISO] {title} para {chave} (tentativa {attempt+1}/{retries})', flush=True)
                if attempt < retries - 1:
                    time.sleep(5)
                    continue
                return None

            loaded = _wait_for_content(page, retries=5, delay=3)
            if not loaded:
                print(f'[AVISO] Conteúdo não carregou {chave} (tentativa {attempt+1}/{retries})', flush=True)
                if attempt < retries - 1:
                    time.sleep(5)
                    try:
                        page.reload(timeout=15000)
                        page.wait_for_load_state('domcontentloaded', timeout=10000)
                    except:
                        pass
                    continue
                return None

            break

        except SessionExpiredError:
            raise
        except Exception as e:
            print(f'[AVISO] Erro {chave} (tentativa {attempt+1}/{retries}): {e}', flush=True)
            if attempt < retries - 1:
                time.sleep(5)
            else:
                return None

    try:
        # ── Header fields (outside tabs) ──────────────────────────────────
        header_fields = {}
        header_panels = page.query_selector_all('.panelExterno')
        for panel in header_panels[:2]:
            header_fields.update(_get_panel_fields(panel))

        chave_acesso = _f(header_fields, 'Chave de acesso') or chave
        data_geracao = _f(header_fields, 'Data de geração', 'Data de geracao')
        numero_dps   = _f(header_fields, 'Número', 'Numero', 'N\u00famero')
        serie        = _f(header_fields, 'Série', 'Serie', 'S\u00e9rie')
        data_emissao = _f(header_fields, 'Data de emissão', 'Data de emissao', 'Data de emiss\u00e3o')

        # ── NFS-e tab (#nfse) ──────────────────────────────────────────────
        nfse_panel  = page.query_selector('#nfse')
        nfse_fields = _get_panel_fields(nfse_panel)

        emit_nome      = _f(nfse_fields, 'Razão Social', 'Razao Social', 'Nome')
        emit_cnpj      = _f(nfse_fields, 'CNPJ') or _f(nfse_fields, 'CPF')
        emit_insc_mun  = _f(nfse_fields, 'Inscrição Municipal', 'Inscricao Municipal')
        emit_regime    = _f(nfse_fields, 'Regime Especial', 'Regime')
        emit_endereco  = _f(nfse_fields, 'Endereço', 'Endereco')
        mun_incidencia = _f(nfse_fields, 'Município de Incidência', 'Municipio de Incidencia', 'Municipio')
        trib_issqn     = _f(nfse_fields, 'Tributação do ISSQN', 'Tributacao do ISSQN')
        v_servico      = _f(nfse_fields, 'Valor do Serviço', 'Valor do Servico')
        desconto       = _f(nfse_fields, 'Desconto incondicionado', 'Desconto')
        base_calculo   = _f(nfse_fields, 'Base de Cálculo', 'Base de Calculo')
        aliquota_iss   = _f(nfse_fields, 'Alíquota', 'Aliquota')
        v_issqn        = _f(nfse_fields, 'Valor do ISSQN')
        ret_issqn      = _f(nfse_fields, 'Retenção', 'Retencao')
        situacao_nfse  = _f(nfse_fields, 'Situação da NFS-e', 'Situacao da NFS-e', 'Situação')

        # ── Pessoas tab (#pessoas) ─────────────────────────────────────────
        pessoas_panel  = page.query_selector('#pessoas')
        pessoas_fields = _get_panel_fields(pessoas_panel)

        toma_cnpj     = _f(pessoas_fields, 'CNPJ') or _f(pessoas_fields, 'CPF')
        toma_nome     = _f(pessoas_fields, 'Nome/Razão Social', 'Nome/Razao Social', 'Nome')
        toma_endereco = _f(pessoas_fields, 'Endereço', 'Endereco')
        toma_telefone = _f(pessoas_fields, 'Telefone')
        toma_email    = _f(pessoas_fields, 'Email')

        # ── Serviço tab (#servicos) ────────────────────────────────────────
        servicos_panel  = page.query_selector('#servicos')
        servicos_fields = _get_panel_fields(servicos_panel)

        cod_tributacao    = _f(servicos_fields, 'Código de Tributação Nacional', 'Codigo de Tributacao')
        desc_servico      = _f(servicos_fields, 'Descrição do serviço', 'Descricao do servico')
        pais_servico      = _f(servicos_fields, 'País', 'Pais')
        municipio_servico = _f(servicos_fields, 'Município', 'Municipio')
        nbs               = _f(servicos_fields, 'Item da NBS', 'NBS')
        doc_resp_tecnica  = _f(servicos_fields, 'documento de responsabilidade técnica', 'documento de responsabilidade tecnica')

        # ── Outros Tributos tab (#tributacao) ──────────────────────────────
        trib_panel  = page.query_selector('#tributacao')
        trib_fields = _get_panel_fields(trib_panel)

        sit_pis_cofins  = _f(trib_fields, 'Situação tributária do PIS/COFINS', 'Situacao tributaria')
        base_pis_cofins = _f(trib_fields, 'Base de cálculo PIS/COFINS', 'Base de calculo PIS')
        pis_aliq        = _f(trib_fields, 'PIS - Alíquota', 'PIS - Aliquota')
        pis_debito      = _f(trib_fields, 'PIS - Débito', 'PIS - Debito')
        cofins_aliq     = _f(trib_fields, 'COFINS - Alíquota', 'COFINS - Aliquota')
        cofins_debito   = _f(trib_fields, 'COFINS - Débito', 'COFINS - Debito')
        desc_ret        = _f(trib_fields, 'Descrição Contribuições Sociais', 'Descricao Contribuicoes')
        v_irrf          = _f(trib_fields, 'IRRF')
        v_csll          = _f(trib_fields, 'Contribuições Sociais - Retidas', 'Contribuicoes Sociais')
        v_inss          = _f(trib_fields, 'Contribuição Previdenciária - Retida', 'Contribuicao Previdenciaria')

        print(f'[DEBUG] {chave} | nfse:{len(nfse_fields)} pessoas:{len(pessoas_fields)} serv:{len(servicos_fields)} trib:{len(trib_fields)} fields', flush=True)

        # ── Parse numeric values ───────────────────────────────────────────
        vServ   = _to_float(v_servico)
        vISSQN  = _to_float(v_issqn)
        vIRRF   = _to_float(v_irrf)
        vCSLL   = _to_float(v_csll)
        vINSS   = _to_float(v_inss)
        # PIS/COFINS debito proprio only counts as retained when desc_ret explicitly says Retidos
        pis_cofins_retidos = bool(desc_ret) and 'Não Retidos' not in desc_ret and 'Nao Retidos' not in desc_ret and desc_ret.strip() not in ('', '-', '0')
        vPIS    = _to_float(pis_debito) if pis_cofins_retidos else 0.0
        vCOFINS = _to_float(cofins_debito) if pis_cofins_retidos else 0.0

        # ── Classification ─────────────────────────────────────────────────
        is_federal   = vIRRF > 0 or vCSLL > 0 or vINSS > 0 or vPIS > 0 or vCOFINS > 0
        is_municipal = '2' in ret_issqn
        is_cancelada = '100' not in situacao_nfse if situacao_nfse else False

        return {
            'chave':             chave_acesso,
            'numero':            numero_dps,
            'serie':             serie,
            'data_emissao':      data_emissao,
            'data_geracao':      data_geracao,
            'situacao':          situacao_nfse,
            'is_cancelada':      is_cancelada,
            'emit_nome':         emit_nome,
            'emit_cnpj':         emit_cnpj,
            'emit_insc_mun':     emit_insc_mun,
            'emit_regime':       emit_regime,
            'emit_endereco':     emit_endereco,
            'mun_incidencia':    mun_incidencia,
            'toma_cnpj':         toma_cnpj,
            'toma_nome':         toma_nome,
            'toma_endereco':     toma_endereco,
            'toma_telefone':     toma_telefone,
            'toma_email':        toma_email,
            'cod_tributacao':    cod_tributacao,
            'desc_servico':      desc_servico,
            'pais_servico':      pais_servico,
            'municipio_servico': municipio_servico,
            'nbs':               nbs,
            'doc_resp_tecnica':  doc_resp_tecnica,
            'trib_issqn':        trib_issqn,
            'v_servico':         vServ,
            'desconto':          _to_float(desconto),
            'base_calculo':      _to_float(base_calculo),
            'aliquota_iss':      _to_float(aliquota_iss),
            'v_issqn':           vISSQN,
            'ret_issqn':         ret_issqn,
            'sit_pis_cofins':    sit_pis_cofins,
            'base_pis_cofins':   _to_float(base_pis_cofins),
            'pis_aliq':          _to_float(pis_aliq),
            'v_pis':             vPIS,
            'cofins_aliq':       _to_float(cofins_aliq),
            'v_cofins':          vCOFINS,
            'v_irrf':            vIRRF,
            'v_csll':            vCSLL,
            'v_inss':            vINSS,
            'is_federal':        is_federal,
            'is_municipal':      is_municipal,
        }

    except SessionExpiredError:
        raise
    except Exception as e:
        print(f'[AVISO] Erro ao parsear Visualizar {chave}: {e}', flush=True)
        return None
