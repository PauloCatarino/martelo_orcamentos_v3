# Martelo V3 — 1.0.16

Corrige o empacotamento da 1.0.15: o instalador completo volta a incluir
PyTorch, Sentence Transformers, Transformers, SciPy e scikit-learn para a
pesquisa por IA. O perfil `full` passa a ser o padrão dos builds.

O build exclui os diretórios das ferramentas auxiliares do agente na procura
de DLLs. Evita a inclusão de um ICU incompatível, que impedia carregar QtCore.
O diagnóstico do executável confirmou o carregamento das bibliotecas de IA
e uma operação PyTorch, sem ligação à base nem envio de dados.

Mantém as funcionalidades da 1.0.15. Não requer nova migração da base.

O Ollama e os modelos de linguagem continuam instalados/configurados à parte
em cada PC, como nas versões anteriores. Incluir as bibliotecas Python não
instala nem descarrega os modelos do Ollama.

Fechar o Martelo, instalar esta versão e confirmar 1.0.16 ao abrir. Testar a
pesquisa por IA num PC que já tenha o índice, modelo e Ollama configurados.
