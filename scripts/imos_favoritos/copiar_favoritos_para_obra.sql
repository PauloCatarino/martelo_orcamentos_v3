/* =====================================================================================
   FAVORITOS DO ARTICLE DESIGNER PARA UMA OBRA  (imos_LE)          preparado a 19-10-2026
   -------------------------------------------------------------------------------------
   Problema: nas obras criadas pelo Martelo, no iX CAD > Article Designer, as listas do
   «Princípio de construção» e da «Informação de produção» abrem vazias.

   Causa (comparação 1804_01_26_JF_VIVA, criada pelo Martelo, com 1804_01_26_JF_VIVA_copia,
   criada à mão no Organizer): ao criar uma obra, o Organizer copia a lista global de
   favoritos (dbo.FAVORITES com INORDER = '', 891 linhas em 47 listas) para a obra nova,
   com INORDER = nome da obra. O Martelo não faz essa cópia, por isso a obra fica sem
   favoritos. As linhas da _copia são iguais, uma a uma, às da lista global.

   O que este script faz: copia a lista global para a obra indicada em @obra.
     - Só copia as listas (LIST_TYPE) que a obra ainda não tem: o que o iX CAD já lá tiver
       gravado fica como está.
     - Só INSERT. Não altera nem apaga nada.

   ANTES DE CORRER: fechar a obra no iX CAD (de preferência, fechar o iX CAD).

   COMO CORRER (SSMS, janela nova ligada à imos_LE):
     a) @ensaio = 1 (como está): faz, mostra e DESFAZ. Ver «ENSAIO OK - nada foi gravado».
     b) @ensaio = 0: grava. Ver «FAVORITOS GRAVADOS na obra ...».

   COMO TESTAR: abrir a obra no iX CAD > Article Designer > escolher um tipo de peça (ex.
   Topo) > seta do «Princípio de construção»: a lista deve trazer os mesmos nomes que a
   _copia (TP_I_2020, TP_O_2222, TP_I_2000_CV_PRF_Ov03_Rf1, ...).
   ===================================================================================== */
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @ensaio bit = 1;   -- 1 = ensaio (desfaz no fim) | 0 = grava

DECLARE @obra nvarchar(30) = N'1804_01_26_JF_VIVA';

/* ---------- verificações antes de mexer ---------- */
IF DB_NAME() <> N'imos_LE'
    THROW 50201, N'FAVORITOS: esta janela não está ligada à imos_LE. Nada foi feito.', 1;
IF @@TRANCOUNT <> 0
    THROW 50202, N'FAVORITOS: há uma transação aberta nesta janela. Abrir uma janela nova.', 1;
IF NOT EXISTS (SELECT 1 FROM PROADMIN WHERE NAME = @obra AND TYPE = 173)
    THROW 50203, N'FAVORITOS: não existe nenhuma encomenda com o nome indicado em @obra. Nada foi feito.', 1;
IF (SELECT COUNT(*) FROM IMORDFOLDER WHERE NAME = @obra AND TYPE = 173) > 1
    THROW 50204, N'FAVORITOS: há mais do que uma encomenda com este nome. Rever antes. Nada foi feito.', 1;
IF NOT EXISTS (SELECT 1 FROM FAVORITES WHERE INORDER = N'')
    THROW 50205, N'FAVORITOS: a lista global de favoritos (INORDER vazio) está vazia. Nada foi feito.', 1;
IF NOT EXISTS (SELECT 1 FROM FAVORITES g
               WHERE g.INORDER = N''
                 AND NOT EXISTS (SELECT 1 FROM FAVORITES o
                                 WHERE o.INORDER = @obra AND o.LIST_TYPE = g.LIST_TYPE))
    THROW 50206, N'FAVORITOS: a obra já tem todas as listas. Já foi aplicado? Nada foi feito.', 1;

DECLARE @antes int = (SELECT COUNT(*) FROM FAVORITES WHERE INORDER = @obra);
DECLARE @global int = (SELECT COUNT(*) FROM FAVORITES WHERE INORDER = N'');

BEGIN TRAN;

INSERT INTO FAVORITES (LIST_TYPE, INORDER, POSITION, NAME)
SELECT g.LIST_TYPE, @obra, g.POSITION, g.NAME
FROM FAVORITES g
WHERE g.INORDER = N''
  AND NOT EXISTS (SELECT 1 FROM FAVORITES o
                  WHERE o.INORDER = @obra AND o.LIST_TYPE = g.LIST_TYPE);

DECLARE @copiadas int = @@ROWCOUNT;

/* ---------- verificação ---------- */
SELECT @obra AS obra, @antes AS linhas_antes, @copiadas AS linhas_copiadas,
       (SELECT COUNT(*) FROM FAVORITES WHERE INORDER = @obra) AS linhas_depois,
       @global AS linhas_lista_global;
-- esperado na 1804_01_26_JF_VIVA: antes 0, copiadas = depois = lista global (891 a 19-10)

SELECT g.LIST_TYPE,
       CASE g.LIST_TYPE
           WHEN 0  THEN N'Materiais'
           WHEN 18 THEN N'Informação de produção'
           WHEN 22 THEN N'Folgas das frentes'
           WHEN 28 THEN N'Lateral'
           WHEN 29 THEN N'Costas'
           WHEN 32 THEN N'Portas'
           WHEN 35 THEN N'Topo'
           WHEN 36 THEN N'Fundo'
           WHEN 37 THEN N'Prateleira amovível'
           WHEN 38 THEN N'Prateleira fixa'
           WHEN 39 THEN N'Divisória'
           WHEN 41 THEN N'Gaveta'
           ELSE N''
       END AS lista,
       COUNT(*) AS na_lista_global,
       (SELECT COUNT(*) FROM FAVORITES o WHERE o.INORDER = @obra AND o.LIST_TYPE = g.LIST_TYPE) AS na_obra
FROM FAVORITES g
WHERE g.INORDER = N''
GROUP BY g.LIST_TYPE
ORDER BY g.LIST_TYPE;
-- esperado: na_obra igual a na_lista_global em todas as linhas

IF @ensaio = 1
BEGIN
    ROLLBACK;
    PRINT N'ENSAIO OK - nada foi gravado. Para gravar: @ensaio = 0 e correr outra vez.';
END
ELSE
BEGIN
    COMMIT;
    PRINT N'FAVORITOS GRAVADOS na obra ' + @obra + N' (' + CAST(@copiadas AS nvarchar(10)) + N' linhas).';
END

/* ---------- PARA DESFAZER depois de gravado (correr à parte, com a obra fechada no iX CAD) ----------
   Tira TODOS os favoritos da obra (também os que o iX CAD lá tenha gravado entretanto); a obra
   volta a ficar como as outras criadas pelo Martelo.
BEGIN TRAN;
DELETE FROM FAVORITES WHERE INORDER = N'1804_01_26_JF_VIVA';
COMMIT;
------------------------------------------------------------------------------------------------------ */
