import importlib, pkgutil, json, traceback

TEST_PACKAGE = 'tests'


def main():
    results = []
    for modinfo in pkgutil.iter_modules(['tests']):
        name = modinfo.name
        if not name.startswith('test_'):
            continue
        fq = f'{TEST_PACKAGE}.{name}'
        try:
            m = importlib.import_module(fq)
            if hasattr(m, 'run_test'):
                out = m.run_test()
            else:
                out = None
            results.append({ 'module': name, 'result': out })
        except Exception as e:
            results.append({ 'module': name, 'error': str(e), 'trace': traceback.format_exc() })
    print(json.dumps(results, indent=2))

if __name__ == '__main__':
    main()
