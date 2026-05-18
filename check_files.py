files = {
    'downloader': r'C:\nfse-automation\src\downloader.py',
    'main': r'C:\nfse-automation\main.py',
    'activate_license': r'C:\nfse-automation\activate_license.py',
    'launch_vbs': r'C:\nfse-automation\launch.vbs',
}
for name, path in files.items():
    content = open(path, encoding='utf-8').read()
    print(f'{name}:')
    if name == 'downloader':
        print(f'  federal: {"federal" in content}')
        print(f'  is_federal: {"is_federal" in content}')
        print(f'  shutil: {"shutil" in content}')
    elif name == 'main':
        print(f'  activate_license: {"activate_license" in content}')
        print(f'  group: {"--group" in content}')
    elif name == 'activate_license':
        print(f'  already active check: {"ACTIVE" in content}')
    elif name == 'launch_vbs':
        print(f'  already running check: {"alreadyRunning" in content}')