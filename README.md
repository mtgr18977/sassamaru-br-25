# Previsão de Jogos Brasileirão - Modelo Híbrido Poisson + Elo

Este projeto implementa um modelo híbrido de previsão de partidas de futebol, combinando a força estatística do modelo de Poisson com o ajuste dinâmico do rating Elo. O objetivo é gerar previsões realistas para jogos do Campeonato Brasileiro, apresentando probabilidades de vitória, empate e derrota, além de palpites e gols esperados para cada time.

## ✨ Funcionalidades

- **Previsão de resultados** para partidas do Brasileirão com base em dados históricos.
- **Cálculo de probabilidades** de vitória, empate e derrota usando distribuição de Poisson ajustada por Elo.
- **Palpite automático** para cada jogo, baseado na maior probabilidade.
- **Saída em tabela Markdown** pronta para uso em posts e relatórios.
- **Fácil calibragem** dos parâmetros de vantagem de casa e influência Elo.

## 🧠 Como funciona

O modelo utiliza:
- **Poisson**: Estima o número esperado de gols para cada time, considerando ataque, defesa e médias da liga.
- **Elo**: Ajusta as expectativas de gols conforme a força relativa dos times e a vantagem de jogar em casa.
- **Simulação de placares**: Calcula a probabilidade de cada resultado possível (mandante, empate, visitante) e define o palpite.

## ⚙️ Requisitos

- Python 3.7+
- pandas

Instale as dependências com:
```bash
pip install pandas
```

## 🚀 Como usar

1. Coloque o arquivo de dados dos jogos (`br-25.csv`) na pasta `sassamaru-br-25/`.
2. Execute o script:
   ```bash
   python sassamaru-br-25/previsao.py
   ```
3. O resultado será impresso em formato Markdown, pronto para copiar e colar em posts.

## 📋 Exemplo de saída

```
# Previsão de Jogos - Modelo Híbrido Poisson + Elo

| Mandante      | Visitante         | Gols Mandante | Gols Visitante | Prob Mandante (%) | Prob Empate (%) | Prob Visitante (%) | Palpite   |
|:------------- |:----------------- | ------------: | -------------: | ----------------: | --------------: | -----------------:|:----------|
| Internacional | Vitoria           |         1.23  |          0.98  |             42.1  |           29.5  |              28.4 | Mandante  |
| Bahia         | Atletico Mineiro  |         1.10  |          1.05  |             35.0  |           33.0  |              32.0 | Empate    |
| ...           | ...               |         ...   |          ...   |             ...   |           ...   |              ...  | ...       |
```

## 🛠️ Calibragem

Se perceber que o modelo está favorecendo demais o mandante ou visitante, ajuste os parâmetros no início do arquivo `previsao.py`:
- `ELO_VANTAGEM_CASA_PADRAO`: Vantagem padrão do mandante (recomendo entre 0 e 80).
- `ELO_INFLUENCE`: Influência do Elo no ajuste dos gols esperados (recomendo entre 0.05 e 0.35).

## 📄 Licença

[Adicione aqui a licença do seu projeto, se aplicável.]

---
Desenvolvido por [Seu Nome]. Sinta-se à vontade para contribuir ou sugerir melhorias!
