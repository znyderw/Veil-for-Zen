# Construção e instalação verificadas

Ambiente: Omarchy 4.0.6, Python 3.14, Qt/PySide6 6.12.0, mesmo computador de desenvolvimento. Terminal sem resolução DNS para PyPI/GitHub.

Licença MIT aplicada ao código original; LICENSE e NOTICE.md são incluídos no wheel/fonte e instalados pelo pacote Arch. O teste em ambiente limpo foi adiado pelo autor.

## Artefatos

- Wheel construído com o backend padrão `setuptools.build_meta`, usando setuptools 83 disponível em um runtime local. Nenhum pacote do sistema foi instalado ou alterado.
- `tools/prepare_release.py` gera a fonte determinística, wheel, PKGBUILD com SHA-256 real e checksums.
- `makepkg --nodeps --nosign --noconfirm` construiu `veil-for-zen-0.9.0beta-1-any.pkg.tar.zst` em diretório temporário. `--nodeps` foi necessário porque setuptools foi fornecido por `PYTHONPATH`, em vez de estar registrado no pacman. Não é uma validação de resolução de dependências numa máquina limpa.
- O pacote foi extraído em uma raiz temporária. O comando empacotado respondeu `--version`; desktop e ícone estavam presentes. O arquivo desktop passou em `desktop-file-validate`.

O fluxo de primeiro uso com oferta de migração e cópia assíncrona também passou em um HOME temporário, via ponto de entrada do código-fonte e Qt offscreen.

## Instalação Python e remoção

O script real `tools/install-local.sh` foi exercitado com HOME/XDG temporários, incluindo espaços no caminho, pip offline e setuptools local. Apenas a criação do venv foi adaptada no teste para `--system-site-packages`, expondo o PySide6 já instalado. Esse teste verifica o fluxo do instalador, empacotamento e caminhos; **não** verifica download/instalação das dependências em um venv totalmente isolado.

- Instalação do pacote, comando, desktop e ícone: passou.
- Comando instalado respondeu `--version`: passou.
- Interface instalada abriu e fechou com sucesso via Qt offscreen, fora da pasta do código-fonte e sem `PYTHONPATH` do projeto: passou.
- `uninstall-local.sh` removeu runtime, comando, desktop e ícone: passou.
- Dados pessoais fictícios e perfil fictício permaneceram intactos: passou.
- Instalação integral em venv isolado com download de PySide6: pendente, rede indisponível.
- Inicialização clicando no menu em uma sessão gráfica nova: pendente.

## Reprodutibilidade e limites

Duas execuções consecutivas produziram fonte e wheel com SHA-256 idênticos. O arquivo fonte usa ordem, proprietário, permissões e timestamp normalizados. A receita referencia seu hash real. A reprodução do build requer a mesma versão das ferramentas de empacotamento; dependências do Arch não estão congeladas em um snapshot de repositório. O teste não afirma identidade binária de pacotes construídos em distribuições ou versões diferentes.

O resultado prepara uma beta local com 80 testes automatizados passando. A matriz de quatro cenários e a confirmação do autor sobre ícones/biblioteca estão registradas em VALIDATION.md. Não substitui o teste completo no Zen e numa instalação limpa descrito em VALIDATION.md.
