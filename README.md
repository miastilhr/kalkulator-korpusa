# v27 – Final (radna i stabilna verzija)
- Full kalkulator (auto dimenzije, Kapa/Pod, police, leđa, fronte, trake, rezanje)
- KV tablice s okvirima, crna tipografija, kompaktan razmak
- PDF export fix (ispravni bytes; datoteka se otvara)
- Spremno za Streamlit Cloud (uključen requirements.txt)

## Pokretanje lokalno
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud (kratko)
1) Gurni `app.py`, `cjenik.json`, `requirements.txt` u GitHub repo
2) Na https://streamlit.io/cloud -> Deploy app -> odaberi repo i `app.py`
3) Dobit ćeš javni link koji radi na mobitelu i računalu
