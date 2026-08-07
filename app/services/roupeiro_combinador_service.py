"""Combinador determinístico de módulos para roupeiros de abrir."""

from __future__ import annotations

from decimal import Decimal

from app.domain.roupeiro_ia import (
    ModuloElegivel,
    POSICAO_CANTO,
    POSICAO_CENTRO,
    POSICAO_DIREITA,
    POSICAO_ESQUERDA,
    POSICAO_REMATE,
    PropostaComposicao,
    PropostaModulo,
)


class RoupeiroCombinadorService:
    """Gera e ordena soluções válidas; não decide preços nem medidas finais."""

    def propor(
        self,
        largura_total_mm: Decimal,
        catalogo: list[ModuloElegivel] | tuple[ModuloElegivel, ...],
        caracteristicas_pedidas: dict[str, Decimal] | None = None,
        *,
        bonus_modulos: dict[int, float] | None = None,
        max_modulos: int = 6,
        limite: int = 3,
    ) -> list[PropostaComposicao]:
        largura_item = Decimal(str(largura_total_mm))
        elegiveis = list(catalogo)
        if not elegiveis:
            return []

        pedidos = {
            str(k).upper(): Decimal(str(v))
            for k, v in (caracteristicas_pedidas or {}).items()
            if Decimal(str(v)) > 0
        }
        bonus = bonus_modulos or {}

        # Os módulos continuam paramétricos: H/L/P e HM/LM/PM só são resolvidos
        # no item/custeio. Aqui combinamos características (portas, gavetas,
        # prateleiras, varões...) e posição, sem repartir a largura do item.
        estados: list[tuple[ModuloElegivel, ...]] = [()]
        candidatos: list[tuple[ModuloElegivel, ...]] = []
        for _profundidade in range(1, max_modulos + 1):
            novos: list[tuple[ModuloElegivel, ...]] = []
            for estado in estados:
                for modulo in elegiveis:
                    sequencia = estado + (modulo,)
                    if self._posicoes_validas(sequencia):
                        candidatos.append(sequencia)
                    novos.append(sequencia)
            novos.sort(
                key=lambda seq: -self._pontuar(
                    seq, pedidos, bonus, penalizar_excesso=False
                )
            )
            estados = novos[:250]
            if not estados:
                break

        propostas: list[PropostaComposicao] = []
        vistos: set[tuple[int, ...]] = set()
        for sequencia in candidatos:
            chave = tuple(m.id for m in sequencia)
            if chave in vistos:
                continue
            vistos.add(chave)
            caracteristicas = self._somar_caracteristicas(sequencia)
            pontuacao = self._pontuar(sequencia, pedidos, bonus)
            componentes = tuple(
                PropostaModulo(
                    def_modulo_id=modulo.id,
                    codigo=modulo.codigo,
                    nome=modulo.nome,
                    ordem=ordem,
                    largura_mm=Decimal("0"),
                )
                for ordem, modulo in enumerate(sequencia, 1)
            )
            cobertura = ", ".join(
                f"{codigo} {caracteristicas.get(codigo, Decimal('0'))}/{quantidade}"
                for codigo, quantidade in pedidos.items()
            ) or "sem características quantitativas reconhecidas"
            explicacao = (
                f"{len(componentes)} módulo(s), avaliados pelas características: {cobertura}. "
                "As medidas continuam a ser resolvidas pelas variáveis do item e do custeio."
            )
            propostas.append(
                PropostaComposicao(componentes, pontuacao, explicacao, largura_item)
            )

        propostas.sort(key=lambda proposta: (-proposta.pontuacao, len(proposta.modulos), tuple(m.codigo for m in proposta.modulos)))
        return propostas[:limite]

    def _pontuar(
        self,
        sequencia: tuple[ModuloElegivel, ...],
        pedidos: dict[str, Decimal],
        bonus: dict[int, float],
        *,
        penalizar_excesso: bool = True,
    ) -> float:
        existentes = self._somar_caracteristicas(sequencia)
        if pedidos:
            falta = sum(
                max(quantidade - existentes.get(codigo, Decimal("0")), Decimal("0"))
                for codigo, quantidade in pedidos.items()
            )
            excesso = sum(
                max(existentes.get(codigo, Decimal("0")) - quantidade, Decimal("0"))
                for codigo, quantidade in pedidos.items()
            )
            pontuacao = 100.0 - float(falta * 18)
            if penalizar_excesso:
                pontuacao -= float(excesso * 4)
        else:
            pontuacao = 60.0
        pontuacao -= max(0, len(sequencia) - 1) * 0.75
        pontuacao += sum(float(bonus.get(modulo.id, 0.0)) for modulo in sequencia)
        return pontuacao

    @staticmethod
    def _posicoes_validas(sequencia: tuple[ModuloElegivel, ...]) -> bool:
        ultimo = len(sequencia) - 1
        for indice, modulo in enumerate(sequencia):
            if modulo.posicao == POSICAO_ESQUERDA and indice != 0:
                return False
            if modulo.posicao == POSICAO_DIREITA and indice != ultimo:
                return False
            if modulo.posicao == POSICAO_CENTRO and len(sequencia) > 1 and indice in (0, ultimo):
                return False
            if modulo.posicao in (POSICAO_CANTO, POSICAO_REMATE) and indice not in (0, ultimo):
                return False
        return True

    @staticmethod
    def _somar_caracteristicas(sequencia) -> dict[str, Decimal]:
        total: dict[str, Decimal] = {}
        for modulo in sequencia:
            for codigo, quantidade in modulo.caracteristicas.items():
                total[codigo] = total.get(codigo, Decimal("0")) + Decimal(str(quantidade))
            if modulo.posicao in (POSICAO_REMATE, POSICAO_CANTO):
                total[modulo.posicao] = total.get(modulo.posicao, Decimal("0")) + Decimal("1")
        return total
