# Contribuir com o Veil

Leia o README e os resultados de validação. O código original é licenciado sob MIT; consulte LICENSE e NOTICE.md. Imagens enviadas em contribuições precisam de origem e licença compatível. Não inclua dados pessoais de mantenedor sem autorização.

Use Python 3.11+ e um ambiente virtual. Instale o projeto com `python -m pip install .` dentro desse ambiente; para construir artefatos, instale `setuptools>=77`.

Execute `QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME= python -m unittest discover -s tests -v`. Testes devem usar perfis fictícios e XDG temporários. Nunca aponte testes automatizados para um perfil real. Verifique a interface com fontes maiores e escalas diferentes; testes offscreen não substituem Wayland/X11 reais.

Mantenha processamento pesado fora da thread da interface. Widgets e pixmaps pertencem à thread gráfica. Preserve configurações antigas na migração, outros mods no perfil e dados pessoais na desinstalação.

Relate problemas com versões de Linux, Python, Qt e Zen, instalação nativa/Flatpak, passos e resultados esperados. Oculte caminhos pessoais e conteúdo privado de screenshots/arquivos de perfil. Não envie perfis completos.

Mudanças no CSS precisam de testes de aplicação, desativação, restauração, falha de permissão e preservação de estilos externos. Seletores internos do Zen exigem validação real. Veja `docs/VALIDATION.md` antes de propor uma release.
