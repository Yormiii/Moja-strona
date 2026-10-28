# Overpass — diagnostyka i uruchomienie z iPada

Tryb `diagnose` nie uruchamia pełnego discovery, nie importuje firm, nie ocenia WWW i nie generuje demo. Używa dotychczasowego prywatnego cache/licznika, odtwarzania stanu i szyfrowania. `discover` pozostaje dostępny. Konfiguracja: `config/overpass.json`.

## Trzy osobne sondy

| Sonda | Żądanie | Co oznacza sukces |
|---|---|---|
| `availability` | GET `/api/status` | HTTP 200 od serwera/gateway; nie dowodzi działania interpretera. |
| `minimal_query` | POST: `[out:json][timeout:5][maxsize:8388608];node(1);out count;` | Interpreter wykonał minimalny odczyt po ID i zwrócił licznik. |
| `industry_small_area` | POST: jedna branża, domyślnie `mechanik`, promień 2000 m od centrum Poznania, `out count;` | Działa małe zapytanie przestrzenne; wynik 0 też jest poprawną odpowiedzią. |

Zapytania mają domyślnie 57 i 116 bajtów. `industry=all` w diagnostyce oznacza **mechanik**, nigdy 30 branż. Można wybrać inny pojedynczy identyfikator. Centrum bierze się z `config/osm.json`, a promień nie przekracza 2 km.

Wynik to **liczba obiektów OSM, nie liczba klientów**. Nie pobieramy nazw/kontaktów w zapytaniach `out count`. Nie zapisujemy rekordów prospects. Diagnostyczne Summary pokazuje sondy, a nie tabelę znalezionych firm i punktacji. Treść `/api/status` może zawierać metadane połączenia; nie jest ujawniana.

## Etapy timeoutu

| Kategoria | Interpretacja |
|---|---|
| `dns_error` | Nie rozpoznano publicznego adresu przed HTTP. |
| `connect_timeout` | Timeout zestawienia TCP, tunelu proxy lub handshake TLS; nie rozdzielamy tych podetapów. |
| `write_timeout` | Timeout wysyłania żądania. |
| `read_timeout` | Brak nagłówków/treści w limicie. Przyczyną może być trasa, gateway, kolejka albo obliczenia serwera. Sam timeout nie rozstrzyga tego. |
| `overpass_timeout` | Overpass zwrócił `remark` potwierdzający przekroczenie czasu wykonania, także przy HTTP 200. |
| `timeout` | Starszy lub wstrzyknięty transport nie podał etapu; nie zgadujemy go na podstawie czasu. |
| `http_429` / `http_5xx` | Otrzymano HTTP; status jest w tabeli. 502/504 nie wskazuje jednoznacznie winnego gateway. |

Nadal używamy `urllib`, proxy środowiska oraz weryfikacji TLS/hosta. Instrumentowane połączenie ma **8 s na zestawienie**, potem **15 s na odczyt sondy**; pełny Overpass zachowuje 35 s, WWW 15 s. Są to timeouty operacji socket, nie łącznego czasu całej pracy. DNS, limiter i narzut protokołów mogą wydłużyć czas w tabeli.

Maksymalnie 3 próby, po jednej na sondę, bez ponowień. Odstęp Overpass minimum 10 s, Retry-After, maks. 10 żądań Overpass/dzień oraz dotychczasowe budżety pozostają w mocy. Limit odpowiedzi sondy 64 KiB, cache 5 minut. `cache` nie jest nowym testem sieci. Po 429/401/403/407/451, długim odroczeniu lub wyczerpaniu budżetu pozostałe sondy są pomijane. Zwykły błąd `/api/status` nie blokuje niezależnego sprawdzenia interpretera.

**Obie instancje współdzielą budżet Overpass i odroczenie w tej samej SQLite.** Zmiana hosta nie resetuje limitu. Ciągłość między runami wymaga `storage=private-repository`. `temporary` nadal nie zachowuje liczników/bazy między runami. Nie resetuj stanu ani nie uruchamiaj serii testów, żeby ominąć limit.

## Ręczny wybór instancji

Domyślna: `overpass-de`. `private-coffee` wybiera `https://overpass.private.coffee/api/interpreter` i wymaga `accept_instance_terms=true`. Nie przyjmujemy dowolnego URL. **Brak automatycznego failover i rotacji hostów.**

Sprawdzono [zasady Private.coffee](https://overpass.private.coffee/) 2026-10-28: bezpłatne użycie komercyjne jest dozwolone; operator zaleca POST, identyfikujący projekt User-Agent, oszczędne zapytania i brak danych osobowych w żądaniu. Nie gwarantuje dostępności. Nasze limity obowiązują także tam. Ręczny wybór nie służy obchodzeniu blokady, 429 ani budżetu. [Zasady overpass-api.de](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html).

## Dokładne kroki na iPadzie

1. W Safari otwórz [aktualny szablon workflow](https://github.com/Yormiii/Moja-strona/blob/feature/demo-generator/prospect-finder/workflow/prospect-finder.yml), wybierz **Raw**, zaznacz wszystko i skopiuj.
2. W prywatnym `Yormiii/webforge-prospect-runner` otwórz `.github/workflows/prospect-finder.yml`, wybierz ołówek, zastąp całą treść i wybierz **Commit changes** na domyślnej gałęzi **tego prywatnego repozytorium**. Nie zmieniaj `main` w `Moja-strona`.
3. **Actions → WebForge Prospect Finder (manual) → Run workflow**. Pozostaw gałąź domyślną prywatnego runnera. Jeśli nie ma pól/przycisku, odśwież lub w Safari wybierz „Poproś o witrynę na komputer”.
4. Ustaw **mode=diagnose**, **instance=overpass-de**, **region=poznan**, **industry=mechanik**. `limit=25` i `category=wszystkie` można pozostawić; są ignorowane przez sondy i nie uruchamiają pełnego wyszukiwania.
5. Zachowaj istniejący `PROSPECT_DATA_KEY` i magazyn. Jeśli masz skonfigurowany trwały stan, wybierz **storage=private-repository**, podaj dotychczasowe `state_repository` i zachowaj token. Nie zmieniaj klucza. Konfiguracja magazynu: [README_ACTIONS.md](README_ACTIONS.md).
6. Dla overpass-de pozostaw `accept_instance_terms` wyłączone. Kliknij **Run workflow** i otwórz nowy przebieg. Testy: **90 Python**. Summary ma pokazać trzy sondy i ich czasy/kategorie, nie klientów. Czerwony job oznacza co najmniej jedną nieudaną sondę; raport nadal pozwala diagnozować.
7. Dla osobno wybranej próby Private.coffee przeczytaj zasady i uruchom nowy ręczny run z **mode=diagnose**, **instance=private-coffee**, zaznaczając **accept_instance_terms**. Zachowaj ten sam trwały magazyn; nie zmieniaj instancji przy aktywnej blokadzie/Retry-After/budżecie.
8. Do analizy udostępniaj tylko kontrolowaną tabelę Summary. Nie przesyłaj sekretów, odszyfrowanej bazy ani surowego statusu. Cache i raport znajdują się też w istniejącej zaszyfrowanej paczce z retencją 1 dzień — nadal nie jest to trwała baza.

Aktualizacja workflow w prywatnym runnerze dodaje nowe pola. Nie używaj ponowienia starego runu do testowania nowego formularza. Kod pobierany jest z `feature/demo-generator` źródłowego repozytorium. Harmonogram, wysyłka i publikacja demo pozostają wyłączone.

## Rzeczywiste sprawdzenia

Odczytano [drugi run 40604723800](https://github.com/Yormiii/webforge-prospect-runner/actions/runs/40604723800): 73 testy, 0 firm, timeouty 35263/35245/35285 ms, bez HTTP, 8 klauzul/901 bajtów. Etapu tych historycznych timeoutów nie da się ustalić wstecz.

Nowe sondy wykonano rzeczywiście w bieżącym środowisku z dostępem sieciowym i zachowanym proxy. **To testy lokalnego wykonawcy, nie nowy GitHub Actions run.**

| Instancja | Status | Minimalne zapytanie | Branża / 2 km |
|---|---|---|---|
| overpass-de | read_timeout, 15426 ms | read_timeout, 15380 ms | HTTP 502, 777 ms |
| private-coffee | read_timeout, 16025 ms | read_timeout, 15829 ms | dns_error przed HTTP |

Instancje wybrano jawnie w dwóch osobnych wywołaniach ze wspólną bazą liczników: łącznie 5 prób HTTP, bez retry/failover. Nie importowano firm. Błędy już przy statusie i minimalnym odczycie wskazują, że ciężkie zapytanie 30 branż nie musi być jedyną przyczyną. Oba serwisy mogły napotkać problem wspólnej trasy/proxy/DNS wykonawcy; nie dowodzi to ich globalnej awarii. Potrzebny jest nowy test w GitHub.

## Darmowa alternatywa dla całej Polski

Rekomendacja: **wyciągi OSM PBF Geofabrik**, zamiast publicznego Overpass jako stałej bazy. Dostępne są [Polska](https://download.geofabrik.de/europe/poland.html) i [Wielkopolska](https://download.geofabrik.de/europe/poland/wielkopolskie.html); przy sprawdzeniu około **2 GB i 152 MB**. Dane mają licencję ODbL i wymagają atrybucji. Nadal mają ograniczenia pokrycia OSM; nie są niezależnym rejestrem firm.

Plan przyszłego adaptera `osm-pbf`:

1. Zacząć od Wielkopolski. Pobrać wyciąg okresowo do prywatnego katalogu, zweryfikować datę/metadane i używać ponownie. Nie pobierać Polski na każde wyszukiwanie.
2. Strumieniowo filtrować obecnymi regułami branż przez [Osmium/pyosmium](https://osmcode.org/osmium-tool/manual.html). Poprawnie odtworzyć geometrię ways/relations z węzłów; PBF nie ma gotowego `center` z Overpass.
3. Przekazać obiekty do obecnego adaptera, zachować źródła/ID OSM, datę wyciągu, deduplikację i konserwatywną punktację. SQLite pozostaje prywatna; bez tagów adresowych nie zgadywać miasta.
4. Rozszerzać województwami, potem filtrować lokalną bazę. Aktualizację danych oddzielić od wyszukiwania; audyt WWW nadal ograniczać istniejącym budżetem.

Adaptera PBF **nie wdrożono ani nie uruchomiono** w tym zadaniu. PBF przekracza obecny budżet HTTP 50 MiB/dzień, więc wymaga osobnego, jawnego budżetu importera. Nie wolno poluzować klienta Overpass. Surowe wyciągi nie mieszczą się w snapshotcie 20 MiB i nie powinny trafiać do Git/publicznych artefaktów; większa SQLite także wymaga innego prywatnego magazynu. Dane są darmowe, ale runner/dysk/magazyn muszą zmieścić się w bezpłatnym przydziale. Nie podłączono płatnych zasobów.

## Testy

`python -m unittest discover -s prospect-finder/tests -v`: 90 przypadków, w tym sondy, rozróżnianie etapów w ścieżce urllib z symulowanymi socketami, TLS/proxy, limity/odroczenia między hostami, ręczny wybór i zasady, prywatność Summary oraz brak wywołania discovery i importu w trybie diagnostycznym. Dane testowe są syntetyczne i nie potwierdzają znalezienia rzeczywistych firm.
