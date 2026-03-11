Suitsy - Financial Portfolio Analytics Dashboard

Suitsy to analityczna aplikacja webowa zbudowana w języku Python z wykorzystaniem frameworka Streamlit. Projekt służy do monitorowania, analizy i wizualizacji wyników portfeli inwestycyjnych w czasie rzeczywistym. System przetwarza historyczne oraz bieżące dane rynkowe, obliczając kluczowe wskaźniki efektywności inwestycji (KPI) i zestawiając je z rynkowymi punktami odniesienia.

# Architektura i Główne Funkcjonalności

Silnik przetwarzania danych: Wykorzystanie biblioteki Pandas do transformacji danych wejściowych, obsługi szeregów czasowych, kalkulacji krzywej kapitału (equity curve) oraz bazy kosztowej.
Kalkulacja wskaźników finansowych: Implementacja modułów wyliczających m.in. Return on Investment (ROI), Maximum Drawdown (maksymalne obsunięcie kapitału) oraz bezwzględne i względne zmiany dzienne.
Integracja danych rynkowych: Agregacja historycznych i bieżących notowań giełdowych oraz kursów walut, co umożliwia wycenę aktywów w czasie rzeczywistym z uwzględnieniem przewalutowań do PLN.
Moduł porównawczy (Benchmarking): Zestawienie stóp zwrotu portfela z głównymi indeksami i aktywami (S&P 500, NASDAQ 100, WIG20, Złoto, Bitcoin) poprzez dynamiczne skalowanie i reindeksowanie szeregów czasowych.
Zarządzanie stanem i UI: Zastosowanie `st.session_state` do obsługi sesji użytkownika. Interfejs oparto na modularnych komponentach z wstrzykniętym niestandardowym arkuszem CSS (Custom Styling).

# Stos Technologiczny

Język programowania: Python 3.9
Frontend / UI Framework: Streamlit
Przetwarzanie i analiza danych: Pandas


# Struktura Katalogów Projektu

Logika aplikacji została podzielona na odseparowane warstwy:

`suitsy_pro.py` - Główny punkt wejścia (entry point) aplikacji, zarządzający konfiguracją i inicjalizacją stanu sesji.
`core/` - Warstwa logiki biznesowej:
`metrics.py` - Moduł matematyczny zawierający funkcje agregujące (`calculate_portfolio_metrics`, `calculate_portfolio_history`).
`data/` - Warstwa dostępu do danych:
`market.py` - Moduł odpowiedzialny za komunikację z API danych rynkowych.
`sheets.py` - Moduł parsujący i ładujący surowe dane wejściowe przypisane do konkretnego identyfikatora użytkownika.
`ui/` - Warstwa prezentacji:
Odseparowane komponenty interfejsu (np. `dashboard.py`, `sidebar.py`) odpowiedzialne za renderowanie metryk i wykresów.

