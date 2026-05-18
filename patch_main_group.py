content = open(r'C:\nfse-automation\main.py', encoding='utf-8').read()

old = '''    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    args = parser.parse_args()

    if args.config:
        with open(args.config, encoding="utf-8") as f:
            run_config = json.load(f)
        companies = run_config["companies"]
        custom_start = run_config.get("start")
        custom_end = run_config.get("end")
    else:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "companies.json"), encoding="utf-8") as f:
            companies = json.load(f)
        custom_start = None
        custom_end = None'''

new = '''    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--group", default=None)
    args = parser.parse_args()

    if args.config:
        with open(args.config, encoding="utf-8") as f:
            run_config = json.load(f)
        companies = run_config["companies"]
        custom_start = run_config.get("start")
        custom_end = run_config.get("end")
    elif args.group is not None or True:
        # try to load from first group in groups.json
        groups_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "groups.json")
        companies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "companies.json")
        try:
            with open(groups_path, encoding="utf-8") as f:
                groups = json.load(f)
            with open(companies_path, encoding="utf-8") as f:
                all_companies = json.load(f)
            # find group by name or use first group
            group = None
            if args.group:
                group = next((g for g in groups if g["name"] == args.group), None)
            if not group and groups:
                group = groups[0]
            if group:
                group_cnpjs = set(group.get("cnpjs", []))
                companies = [c for c in all_companies if c["cnpj"] in group_cnpjs]
                print(f"[OK] Usando grupo: {group['name']} ({len(companies)} empresas)")
            else:
                companies = all_companies
                print("[INFO] Nenhum grupo encontrado, usando todas as empresas")
        except Exception as e:
            print(f"[AVISO] Erro ao carregar grupos: {e}, usando companies.json")
            with open(companies_path, encoding="utf-8") as f:
                companies = json.load(f)
        custom_start = None
        custom_end = None'''

if old in content:
    with open(r'C:\nfse-automation\main.py', 'w', encoding='utf-8') as f:
        f.write(content.replace(old, new))
    print('OK')
else:
    print('ERROR - string not found')