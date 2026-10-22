# Crypto Analytics Dashboard

Dashboard interactiv de analiză crypto construit cu **Streamlit** și **Python**, folosind date live de la CoinGecko.

## Funcționalități

- Prețuri live pentru BTC, ETH, SOL, BNB, XRP
- Variație 24h cu indicator vizual
- Grafic de evoluție a prețului (24h → 1 an)
- Statistici per perioadă: maxim, minim, variație %, volatilitate

## Rulare locală

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Tehnologii

- [Streamlit](https://streamlit.io/)
- [Plotly](https://plotly.com/python/)
- [CoinGecko API](https://www.coingecko.com/en/api)
