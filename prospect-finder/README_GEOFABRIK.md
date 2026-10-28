# Geofabrik — pierwszy test pobierania PBF w Actions

Tryb **`geofabrik-test`** sprawdza źródło i koszt pobierania. **Nie importuje firm**, nie uruchamia Overpass, audytu WWW, generatora ani wysyłki. Istniejąca SQLite, statusy, deduplikacja, scoring i szyfrowanie pozostają zachowane. Pełny adapter PBF jest zaprojektowany poniżej, ale jeszcze nie wdrożony.

## Źródło i wybór wycinka

Sprawdzono publiczne wyciągi [Wielkopolski](https://download.geofabrik.de/europe/poland/wielkopolskie.html) i [listę województw](https://download.geofabrik.de/europe/poland.html). Wielkopolska ma około 152 MiB; mniejsza opcja to Opolskie, około 52 MB, najmniejszy plik województwa na sprawdzonej liście. Obie konfiguracje są dostępne. Opolskie służy wyłącznie testowi źródła, nie szukaniu firm z Poznania. Nie dodano pobierania całej Polski.

To OSM na licencji ODbL z atrybucją „© OpenStreetMap contributors”, wyciąg Geofabrik. Dane nie są pełnym rejestrem firm i nie potwierdzają ich aktywności. [Szczegóły techniczne Geofabrik](https://download.geofabrik.de/technical.html).

Konfiguracja: `config/geofabrik.json`. Profile:

| Profil | Zakres |
|---|---|
| `wielkopolskie-sample` | HEAD/metadane i próbka 1 MiB przez Range; domyślny pierwszy test |
| `wielkopolskie-full` | Pełny wyciąg Wielkopolski, pomiar i MD5 |
| `opolskie-sample` | Analogiczna próbka mniejszego województwa |
| `opolskie-full` | Pełny mniejszy wyciąg do porównania zasobów |

## Co mierzy i weryfikuje kod

1. HEAD pobiera rozmiar i prywatnie zachowuje ETag/Last-Modified. Obsługuje 304 oraz najwyżej dwa przekierowania, tylko HTTPS w obrębie wybranego wycinka na `download.geofabrik.de`. Przekierowanie latest → plik datowany jest normalne.
2. Próbka wymaga HTTP 206 i dokładnego Content-Range. Jeśli serwer ignoruje Range, test **zatrzymuje się przed odczytem pełnego pliku**. Nie ma cichego przejścia na pełne pobranie.
3. Pełny profil pobiera sumę MD5 operatora, następnie plik strumieniowo. Bufor to 1 MiB; PBF nie jest ładowany w całości do RAM. Warunek If-Match/If-Unmodified-Since chroni przed zmianą pliku między HEAD i GET.
4. Oba profile sprawdzają pierwszy nagłówek BlobHeader PBF. Pełny dodatkowo porównuje MD5, liczy SHA-256 i sprawdza liczbę bajtów. MD5 to kontrola zgodności transferu z sumą operatora, nie niezależny kryptograficzny dowód autentyczności; TLS pozostaje weryfikowany. Nie jest to jeszcze pełne parsowanie encji/geometrii PBF.
5. Raport podaje rozmiar, faktyczne pobrane bajty, czas pobierania treści i całego przebiegu, statusy HTTP, szczytowe RSS procesu oraz użycie cache i wynik integralności. `download_ms` nie obejmuje DNS/HEAD/oczekiwania na nagłówki; `elapsed_ms` obejmuje te etapy. Nie przelicza czasu pełnego transferu z próbki.

**RAM:** `rss_peak_bytes` to rzeczywisty szczyt procesu testowego na Ubuntu, obejmujący Python i wrapper. Nie jest wymaganiem pamięci przyszłego importera. Strumieniowy downloader używa bufora 1 MiB i małego prefiksu nagłówka. Dla parsera pyosmium, indeksu węzłów i geometrii trzeba wykonać osobny benchmark; nie obiecujemy mu obecnych 24 MiB.

**Osobny budżet testu źródła:** maks. 256 MiB na plik, 384 MiB/dzień z rezerwacją przed żądaniem, 8 żądań/przebieg i 12/dzień, odstęp 5 s, connect 8 s, odczyt 30 s, termin 300 s sprawdzany między operacjami. Pojedyncza blokująca operacja może dodać swój timeout. Wymagane wolne miejsce: rozmiar pobrania + 32 MiB. Brak automatycznych ponowień dużego transferu. Retry-After jest zachowywany, także między runami i po północy przy trwałym stanie. Nie zwiększono limitu 50 MiB ani innych limitów dotychczasowego klienta Overpass/WWW.

Pobieranie zachowuje proxy, weryfikację TLS i ochronę DNS przed adresami prywatnymi. URL i profile są z allowlisty; nie ma dowolnego adresu z formularza. Nieobsługiwane kodowanie, błędny rozmiar/suma/nagłówek, zmiana metadanych, brak dysku, budżet lub timeout zatrzymują test. Plik `.part` nie jest używany jako gotowy wyciąg.

## Prywatność i cache — co już działa

- W Actions surowy PBF trafia do prywatnego katalogu tymczasowego **poza checkoutem, katalogiem wyników i archiwizowanym drzewem stanu**. Po teście katalog jest usuwany, również przy błędzie. Nie ma PBF w Git, Cloudflare, Actions cache ani artefakcie.
- Raport pokazuje wyłącznie kontrolowane kody, liczby i techniczny hash; nie pokazuje firm, kontaktów, surowych nagłówków, URL z odpowiedzi ani ścieżek prywatnych. Liczniki znalezionych firm w tym trybie są „nie dotyczy/nieustalone”, nie zmyślone 0/25.
- Dotychczasowy artefakt zawiera tylko GPG AES-256: mały raport, SQLite i cache/liczniki. Retencja nadal 1 dzień. Opcjonalny backend prywatnego repozytorium przechowuje zaszyfrowany snapshot baz, **bez PBF**. Limit snapshotu 20 MiB nie jest zwiększony.
- Nowe małe tabele `pbf_usage` i `pbf_metadata` są w istniejącej prywatnej `network-cache.sqlite3`. Przy `storage=private-repository` przechodzą do kolejnych runów; `temporary` nie zapewnia trwałości budżetów.
- Funkcja lokalna może użyć zachowanego prywatnego katalogu cache: istniejący kompletny plik o właściwym rozmiarze jest ponownie hashowany i porównywany z aktualną sumą operatora. Jeśli pasuje, nie jest pobierany ponownie. Konkurujące operacje blokuje lock. W standardowym Actions cache surowego pliku **nie jest trwały** — każdy jawny test `full` mierzy regionalne pobranie od nowa. Nie myl cache metadanych 304 z posiadaniem całego PBF.

## Pierwszy test z iPada — dokładne kroki

1. W Safari otwórz [aktualny szablon](https://github.com/Yormiii/Moja-strona/blob/feature/demo-generator/prospect-finder/workflow/prospect-finder.yml), wybierz **Raw**, zaznacz wszystko i skopiuj.
2. W prywatnym **Yormiii/webforge-prospect-runner** otwórz `.github/workflows/prospect-finder.yml`, kliknij ołówek, zastąp całą treść i wybierz **Commit changes** na domyślnej gałęzi **tego prywatnego runnera**. Nie zmieniaj `main` w `Moja-strona`.
3. **Actions → WebForge Prospect Finder (manual) → Run workflow**. Pozostaw domyślną gałąź prywatnego runnera. W razie braku nowych pól odśwież stronę lub w Safari wybierz „Poproś o witrynę na komputer”.
4. Ustaw **mode = geofabrik-test**, **geofabrik_profile = wielkopolskie-sample**. Pola region, industry, limit, category, instance i akceptacja zasad Overpass nie sterują tym testem — pozostaw domyślne wartości. Overpass nie będzie wywołany.
5. Zachowaj istniejący sekret **PROSPECT_DATA_KEY** i wybrany magazyn. Jeśli masz skonfigurowany backend, użyj **storage=private-repository**, dotychczasowego `state_repository` i tokenu. Nie zmieniaj klucza. Konfiguracja: [README_ACTIONS.md](README_ACTIONS.md).
6. Kliknij **Run workflow**, otwórz nowy przebieg. Testy: **107 Python**. Summary powinno mieć tytuł „test źródła Geofabrik”, rozmiar pliku, próbkę 1048576 bajtów, `pbf_header_valid=true`, czas i RSS. `checksum_verified=false` jest prawidłowe dla próbki. Nie oznacza znalezienia klientów.
7. Po sukcesie próbki uruchom **osobny nowy run** z **mode=geofabrik-test**, **geofabrik_profile=wielkopolskie-full**, zachowując magazyn/sekrety. To pełny benchmark: oczekuj `checksum_verified=true`, pobranych bajtów równych rozmiarowi i pomiaru czasu/RAM. Możesz zamiast tego wybrać `opolskie-full` dla mniejszego pliku. Respektuj budżet i nie uruchamiaj serii pobrań.
8. Do analizy wystarczy Summary. Nie udostępniaj sekretów, baz ani surowych wyciągów. W razie błędu podaj profil, kategorię, HTTP i kontrolowane liczby. Artefakt GPG nie jest trwałą bazą i nie zawiera surowego PBF.

Workflow ma 10 pól wejściowych, ręczny trigger, przypięte akcje i `contents:read`. Nie ma nowego harmonogramu ani publikacji danych. Nowy formularz wymaga aktualizacji prywatnego runnera; samo ponowienie starego runu nie doda pól. Kod pochodzi z `feature/demo-generator` w źródłowym repozytorium.

## Rzeczywisty test lokalny — wynik

Poniższe pomiary wykonano z bieżącego środowiska przez odziedziczone proxy, **nie w GitHub Actions**. Profile dotyczyły tego samego wyciągu Wielkopolski.

| Miara | Próbka | Pełny plik |
|---|---:|---:|
| Rozmiar źródła | 159490674 B | 159490674 B |
| Pobrana treść PBF | 1048576 B | 159490674 B |
| Czas pobierania treści | 1242 ms | 12191 ms |
| Cały przebieg | 18495 ms | 33799 ms |
| Szczyt RSS procesu | 23461888 B (~22,4 MiB) | 25481216 B (~24,3 MiB) |
| Liczba żądań z przekierowaniami | 3 | 4 |
| Nagłówek PBF poprawny | tak | tak |
| MD5 operatora zgodne | nie badano całości | tak |

Pełny plik miał SHA-256 `25eb3d2c107b65a182950c3114b7b28e28980ff856fbc23b682c567d873f8f70`. Wyniki są zależne od dnia, trasy i runnera. Lokalny sukces potwierdza możliwość pobrania; pomiar nowego Actions wymaga ręcznego runu. Nie importowano ani nie oceniano firm. Raporty i lokalny cache są poza repozytorium w prywatnym katalogu wykonawcy.

## Projekt filtrowania lokalnego — kolejny etap

Docelowy przepływ: **odświeżenie wyciągu → lokalny adapter PBF → istniejąca walidacja i Store.ingest → prywatna SQLite → wielokrotne wyszukiwanie i panel**. Zapytania użytkownika nie pobierają PBF i nie korzystają z Overpass.

1. Nowy adapter `osm-pbf` czyta PBF strumieniowo przez pyosmium/osmium. Używa istniejących reguł 30 branż z `config/osm.json` i funkcji klasyfikacji; specyficzne branże zachowują pierwszeństwo. Nie tworzymy drugiej ręcznej listy branż. Zamknięte/prywatne obiekty i obiekty bez nazwy pomijamy jak w obecnym źródle.
2. Węzły mają współrzędne; dla ways/relations trzeba zachować referencyjne węzły i odtworzyć geometrię, z indeksem lokalizacji na dysku. Sam filtr tagów usuwający węzły geometrii byłby błędem. Osobny benchmark ustali pamięć i czas parsera, zanim będzie włączony import.
3. Lokalizacja: znormalizowane miasto z adresu, województwo i kraj z wiarygodnych tagów lub granic administracyjnych, współrzędne i indeks SQLite RTree do promienia/bbox. Wyciąg zawiera kompletne obiekty przecinające granicę i może mieć bufor; nazwa pliku lub `.poly` nie dowodzi przynależności administracyjnej. Nie zgadujemy miasta ani województwa przy braku danych. Dla całej Polski bazę budujemy województwami, nie jednym zapytaniem sieciowym.
4. WWW: filtr `known_url` to poprawny URL z tagów, **nie potwierdzona dostępność HTTP**. `unknown` obejmuje brak tagu oraz website=no; `confirmed_missing` wymaga osobnego, udokumentowanego dowodu. Dostępność/usterki HTTP sprawdza dopiero opcjonalny, limitowany SiteAuditor; podstawowe wyszukiwanie offline go nie uruchamia.
5. Rekord zachowuje typ/ID OSM i źródło, datę wyciągu/importu, kontakty wraz z pochodzeniem, fakty i oznaczenie rzeczywistego źródła. `Store.ingest` zapewnia dotychczasową deduplikację i zachowanie statusów. Aktualizacja OSM ani podany URL nie oznaczają aktywnej firmy; nie dodajemy punktów bez dowodów. Kategoria modernizacji pozostaje niezależna od branży.
6. Punktacja 0–100, statusy, zgoda na kontakt, prywatne eksporty, panel i most do generatora pozostają istniejące. Test źródła nie akceptuje firmy, nie nadaje kontaktu i nie publikuje demo.

## Cache i aktualizacje docelowe

Na początek ręczne odświeżanie Wielkopolski np. raz w tygodniu; między odświeżeniami wyszukujemy wyłącznie w SQLite. Metadane ETag/Last-Modified oraz suma pliku decydują o zmianie wersji. Prywatny zachowany PBF może być ponownie użyty przez moduł, ale na efemerycznym runnerze trzeba w przyszłości zapewnić osobny prywatny magazyn/worker — surowe 152 MiB nie mieści się w obecnym snapshotcie 20 MiB. Nie skonfigurowano takiej usługi ani płatnych zasobów.

Geofabrik publikuje [regionalne aktualizacje `.osc.gz`](https://download.geofabrik.de/technical.html). W późniejszej wersji można je stosować z zapisaną sekwencją replikacji i bazowym PBF, obsługując zmiany/usunięcia oraz weryfikację wyniku. Na start pełne regionalne odświeżenie jest prostsze. Aktualizacja nie może usuwać historii relacji z klientem ani uznawać nieobecności w wyciągu za nieaktywność firmy. Harmonogram nadal jest wyłączony.

Dla pierwszych 20–30 wyników można przechować tylko przefiltrowaną SQLite w dotychczasowym szyfrowanym backendzie, o ile mieści się w 20 MiB. Surowy regionalny plik może pozostać jednorazowy. Rozszerzenie na całą Polskę wymaga pomiarów miejsca, RAM i osobnego planu przechowywania. Darmowe dane nie oznaczają nieograniczonego runnera/dysku; pozostajemy w bezpłatnym przydziale Actions.

## Testy automatyczne

`python -m unittest discover -s prospect-finder/tests -v` — 107 przypadków. Nowe testy używają jawnie syntetycznych nagłówków PBF i symulowanego HTTP. Sprawdzają Range bez fallbacku, strumieniowe czytanie, checksum/truncation, HTML podszywający się pod PBF, cache/304 i uszkodzony cache, DNS/allowlist/przekierowania, budżety/Retry-After, brak dysku, termin/lock, prywatność Summary i brak PBF w odszyfrowanym artefakcie. Nie są wynikiem znalezienia prawdziwych firm.
