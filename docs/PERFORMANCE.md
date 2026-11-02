# Medições locais de performance

Medição única exploratória no mesmo computador: Omarchy 4.0.6, Python 3.14, Qt 6.12, offscreen. Biblioteca de 15 imagens e prévia de 250 × 900 pixels. Não é benchmark estatístico nem promessa para outros computadores. A base foi exportada do commit `1680b15` para uma pasta temporária.

| Operação | Studio original | Veil |
|---|---:|---:|
| Importações e QApplication | 171.005 ms | 166.870 ms |
| Janela até prévia/biblioteca prontas (offscreen) | 245.673 ms | 157.230 ms |
| Primeira leitura da biblioteca | 118.815 ms | 144.434 ms |
| Leitura repetida da biblioteca | 118.186 ms | 5.010 ms |
| Primeira renderização | 112.237 ms | 82.595 ms |
| Mesma renderização repetida | 69.643 ms | 0.052 ms |
| Renderização com brilho em 125% | 87.220 ms | 94.627 ms |
| Pico RSS do processo | 148.2 MiB | 134.7 MiB |

O fundo sólido levou 0.098 ms no Veil, sem ler ou filtrar uma imagem. Esse modo não existia na base. O pico RSS inclui renderizações e janela; o modo sólido adiciona uma operação diferente à medição, e uma única amostra não permite concluir redução sustentada de RAM.

A primeira leitura da biblioteca ficou mais lenta por gravar miniaturas persistentes; a leitura repetida caiu de 118.2 para 5.0 ms. A aplicação de um filtro novo não teve ganho nesta amostra: 87.2 versus 94.6 ms. O benefício principal é evitar recalcular resultados repetidos, não acelerar todos os filtros.

A biblioteca limita cada lote a 48 imagens. O cache de imagem decodificada guarda três entradas com dimensão máxima de 2400; o cache de renderização guarda três resultados. Os filtros continuam sendo calculados em QImage no worker. Não foi introduzida dependência adicional para imagens. Miniaturas e backups em disco ainda não têm expiração automática.

A inicialização da janela foi medida depois dos probes de renderização, com caches aquecidos; não representa uma primeira abertura com cache frio. Inicialização clicando no menu, latência de interação e memória em bibliotecas grandes precisam de medição numa sessão gráfica real. Para repetir: `python tools/benchmark.py /caminho/biblioteca`.
