# Prospect Finder v0.3 — ręczne uruchamianie w GitHub Actions

**Test nowego źródła:** aktualny workflow dodaje `mode=geofabrik-test` i pole `geofabrik_profile` (domyślnie `wielkopolskie-sample`). Nie wywołuje wtedy Overpass ani importu firm. Skopiuj aktualny szablon do prywatnego runnera; instrukcja iPada, pomiary i zasady cache: [README_GEOFABRIK.md](README_GEOFABRIK.md). Aktualnie 107 testów Python; niższe liczby w historycznych sekcjach dotyczą wcześniejszych wersji.

**Nowe sondy po drugim runie:** skopiuj aktualny szablon workflow do prywatnego runnera, aby dodać pola `mode`, `instance`, `accept_instance_terms`. Do testu wybierz `mode=diagnose`; pełne wyszukiwanie pozostaje pod `discover`. Instrukcja iPada i interpretacja etapów: [README_DIAGNOSTICS.md](README_DIAGNOSTICS.md). Aktualny zestaw obejmuje 107 testów Python; wcześniejsze liczby poniżej opisują historyczne runy.

Uruchamia istniejące wyszukiwanie v0.2 w Pythonie na standardowym runnerze Ubuntu. Bez wysyłki, publikacji demo, płatnego API ani zmian produkcyjnego WebForge. Harmonogram **nie jest włączony**. Plik workflow jest zapisany jako JSON, czyli poprawny podzbiór YAML; rozszerzenie `.yml` pozostaje wymagane przez Actions.

## Ważne: dlaczego sam plik na feature nie wystarczy

GitHub wymaga obecności pliku `workflow_dispatch` na **domyślnej gałęzi repozytorium**, aby ręcznie wywołać workflow. W `Yormiii/Moja-strona` jest to `main`, którego nie wolno nam zmieniać. Samo dodanie pliku na `feature/demo-generator` nie sprawi więc, że pojawi się działający przycisk Run workflow. Parametr `--ref` ani REST API nie obchodzą rejestracji workflow na domyślnej gałęzi. [Dokumentacja GitHub](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)

**Rozwiązanie bez dotykania main WebForge:** małe, prywatne repozytorium sterujące, np. `Yormiii/webforge-prospect-runner`. Zawiera workflow na swojej domyślnej gałęzi i pobiera kod z publicznego `Yormiii/Moja-strona`, zawsze z `feature/demo-generator`. Komputer użytkownika nie uczestniczy w przebiegu.

Źródłowy plik do skopiowania: [workflow/prospect-finder.yml](workflow/prospect-finder.yml). Docelowa lokalizacja: `.github/workflows/prospect-finder.yml`. Kopia w głównym katalogu workflow projektu jest identyczna, jeżeli integracja GitHub zezwala na zapis plików workflow.

## Pierwsze uruchomienie — dokładna instrukcja z panelu GitHub

1. W GitHub wybierz **New repository**. Nazwij je `webforge-prospect-runner`, ustaw **Private** i zaznacz utworzenie README. Nie zmieniaj ustawień ani gałęzi `main` repozytorium `Moja-strona`.
2. Otwórz podany wyżej plik źródłowy workflow, wybierz **Raw** i skopiuj całą zawartość. W nowym prywatnym repozytorium wybierz **Add file → Create new file**, wpisz `.github/workflows/prospect-finder.yml`, wklej plik i zatwierdź na domyślnej gałęzi **tego prywatnego repozytorium**. Nie kopiuj baz ani eksportów. Jeśli Actions są wyłączone, włącz je tylko w nowym repozytorium.
3. Wygeneruj losowy klucz **64 znaków hex** (32 losowe bajty), np. zaufanym generatorem haseł lub lokalnym `openssl rand -hex 32`. Zachowaj jego prywatną kopię — utrata klucza uniemożliwia odszyfrowanie. Nie wpisuj go do kodu, issue ani rozmowy.
4. W prywatnym repozytorium przejdź do **Settings → Secrets and variables → Actions → New repository secret**. Nazwa: `PROSPECT_DATA_KEY`; wartość: wygenerowany klucz. Bez poprawnego sekretu job zatrzyma się przed wyszukiwaniem.
5. Wybierz **Actions → WebForge Prospect Finder (manual) → Run workflow**. Pozostaw domyślną gałąź prywatnego repozytorium. Ustaw `region=poznan`, `industry=all`, `limit=25`, `category=wszystkie`, `storage=temporary`; `state_repository` pozostaw puste. Kliknij **Run workflow**.
6. Po zakończeniu otwórz przebieg. **Summary** pokaże wyłącznie liczby i kontrolowane komunikaty. W **Artifacts** pojawi się `webforge-prospects-<run_id>` z plikiem `results.tar.gpg` — tylko jeśli szyfrowanie powiodło się. Retencja: **1 dzień**. Nie jest to trwała baza.
7. Pełne nazwy, kontakty, źródła, CSV/JSON, surowe błędy i SQLite są w zaszyfrowanej paczce. Nie ma ich w publicznych logach ani repozytorium. Paczkę pobierz przed upływem retencji; nie wklejaj jej odszyfrowanej do publicznego GitHub lub Cloudflare.

To jednorazowa konfiguracja. Kolejne ręczne uruchomienia odbywają się w chmurze przez ten sam przycisk. Wybór branży to identyfikator z `config/industries.json` albo `all`; region pochodzi z `config/osm.json`. Limit jest walidowany: 1–30 firm. Domyślnie 25. Kategoria `modernizacja` filtruje eksport po ocenie stron, nie ogranicza źródła do jednej branży.

Nie utworzono automatycznie prywatnego repozytorium, sekretów ani tokenów. Bez tej konfiguracji nie ma potwierdzonego przebiegu w Actions i nie wolno przedstawiać syntetycznych testów jako wyszukanych firm.

## Trwała baza między przebiegami — opcja zalecana

Artefakty mają termin ważności, mogą zostać usunięte i nie zapewniają ciągłości SQLite. Cache Actions też nie jest bazą i nie jest używany. Dla niewielkiej skali v0.3 przygotowano magazyn: **osobne prywatne repozytorium z zaszyfrowanym snapshotem SQLite i cache/liczników sieciowych**. Może to być to samo nowe prywatne repozytorium sterujące. Źródłowe `Yormiii/Moja-strona` jest jawnie zabronione jako magazyn.

Konfiguracja:

1. Prywatne repozytorium magazynu musi być zainicjowane (README wystarczy). Nie włączaj w nim Pages ani publikacji Cloudflare.
2. Utwórz fine-grained PAT ograniczony do **wyłącznie tego prywatnego repozytorium**, z **Contents: read and write**. Metadata read jest dodawane przez GitHub. Tokenu nie dodawaj do publicznego projektu.
3. Dodaj token jako sekret `PROSPECT_STATE_TOKEN` w repozytorium uruchamiającym workflow. Ten sam `PROSPECT_DATA_KEY` musi pozostać dostępny w każdym przebiegu.
4. Uruchom workflow z `storage=private-repository` i `state_repository=Yormiii/webforge-prospect-runner` (lub rzeczywistą nazwą innego prywatnego magazynu).

Przebieg sprawdza przez API, że magazyn jest prywatny, odczytuje `state/prospect-state.tar.gpg`, odszyfrowuje i odtwarza `prospects.sqlite3` oraz `live/network-cache.sqlite3` **poza checkoutem**, w `$RUNNER_TEMP`. Po wyszukiwaniu tworzy spójny backup SQLite i zapisuje nowy zaszyfrowany snapshot na domyślnej gałęzi prywatnego magazynu. Nie zapisuje nic do `main` WebForge. Statusy i historia, deduplikacja, cache i dzienne limity przechodzą do następnego przebiegu.

Zapis używa SHA odczytanej wersji: konflikt nie jest nadpisywany siłowo. Repozytorium jest ponownie sprawdzane przed zapisem; jeśli stało się publiczne, zapis jest blokowany. Zły klucz, błędne archiwum, problem odczytu lub brak uprawnień **nie powodują cichego startu od pustej bazy**. Nowa baza powstaje tylko przy potwierdzonym braku pliku w zweryfikowanym prywatnym magazynie.

Limit zaszyfrowanego pliku stanu to 20 MiB, rozwiniętych baz 150 MiB. To prosty backend dla prototypu i małej liczby ręcznych przebiegów; historia binarnych commitów rośnie. Przy większej skali potrzebny będzie prywatny magazyn obiektowy/serwer, zaprojektowany osobno. Nie podłączono teraz takiej usługi i nie uruchomiono żadnego płatnego magazynu.

`temporary` **nie odtwarza automatycznie wcześniejszej bazy**: liczby nowych/duplikatów odnoszą się do stanu danego przebiegu. Aby deduplikacja i limity były trwałe, wybierz `private-repository`. Zmiana klucza wymaga wcześniejszej kontrolowanej migracji starego snapshotu, nie samej podmiany sekretu.

## Prywatność, artefakty i odczyt wyników

Artefakty repozytorium publicznego nie są prywatnym schowkiem: zalogowana osoba z dostępem odczytu może je pobrać. Dlatego workflow wysyła **wyłącznie** plik GPG zaszyfrowany AES-256, z ochroną integralności OpenPGP. Klucz jest przekazywany do GPG przez deskryptor pipe, nie argument procesu, repozytorium ani plik hasła. [Dostęp do artefaktów — GitHub](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts)

Workflow ma `contents: read`, stałe źródło kodu, brak zapisu poświadczeń checkoutu i akcje przypięte do SHA. Wywołania są wyłącznie ręczne, serializowane wspólną grupą concurrency. Nie ma `push`, `pull_request`, aktywnego `schedule`, publicznego API ani uruchamiania kodu nieznanej gałęzi z wejścia formularza. Token magazynu jest wysyłany tylko do `api.github.com`, bez podążania za przekierowaniem.

Pełne dane pozostają w katalogu tymczasowym runnera i w szyfrowanej paczce/prywatnym magazynie. Publiczne Summary zawiera tylko liczniki, wartości najwyższych punktacji bez identyfikatorów, statystyki WWW i kontrolowane kody błędów. Nazwy i kontakty znajdziesz w prywatnym JSON/CSV, nie w Summary. Pusty lub zablokowany przebieg jest raportowany uczciwie, bez dopisywania firm.

Odszyfrowanie na zaufanym prywatnym komputerze/środowisku z Pythonem i GPG:

```sh
# Ustaw PROSPECT_DATA_KEY w prywatnym środowisku; nie zapisuj wartości w pliku projektu.
python prospect-finder/cloud_runner.py decrypt --input /prywatne/results.tar.gpg --output /prywatne/results.tar.gz
# Rozpakuj TAR.GZ wyłącznie do prywatnego katalogu, nigdy do checkoutu/Cloudflare.
```

W paczce są SQLite oraz eksporty z `live/`; JSON można otworzyć w istniejącym panelu iPada po prywatnym odszyfrowaniu. Samo wyszukiwanie nie wymaga włączonego komputera użytkownika. Nie dodano webowego odszyfrowywania GPG ani panelu online do prywatnej bazy.

Przy normalnym błędzie sieci workflow zachowuje zaszyfrowane wyniki i próbuje zapisać licznik/cache w prywatnym magazynie. Błąd zapisu stanu daje czerwony job; zaszyfrowany artefakt pozostaje kopią do ręcznego odzyskania przed wygaśnięciem. Przy twardym anulowaniu/timeout może nie powstać nowy snapshot ani artefakt — ostatni poprawny snapshot zostaje w magazynie. Nie traktuj artefaktów jako backupu długoterminowego.

## Raport każdego przebiegu

Podsumowanie zawiera:

- liczbę faktycznie znalezionych firm;
- nowe rekordy i już znane/duplikaty względem odtworzonej SQLite;
- liczbę rekordów z podanym WWW (niekoniecznie działającym);
- liczbę potencjalnych modernizacji;
- najwyższe wartości 0–100 i pokrycie dowodami;
- statystyki kontroli WWW, stan odtworzenia bazy oraz błędy i ograniczenia.

Brak uruchomienia (np. brak klucza) oznacza **nieustalone**, nie „znaleziono 0”. Błąd źródła po rzeczywistej próbie może dać 0 i czerwony job. `preflight_failed`: sprawdź parametry/klucz/GPG; `state_restore_failed`: prywatność, token, plik i klucz; `discovery_blocked_or_failed`: źródło/DNS/limity; `packaging_failed`: backup/szyfrowanie; `state_save_failed`: token, konflikt SHA lub limit stanu. Szczegóły dotyczące firm/stron nigdy nie są drukowane w logu.

## Koszt i późniejszy harmonogram

Używany jest standardowy runner Ubuntu i bezpłatny Overpass. Nie uruchomiono płatnych API, większych runnerów ani nowej usługi. GitHub udostępnia darmowe standardowe runnery dla publicznych repozytoriów, a prywatne mają limity minut i miejsca według planu; przekroczenie może być płatne. Dla wymogu 0 zł pozostań w bezpłatnym przydziale i ustaw blokadę wydatków na Actions. Nie włączaj płatnego przekroczenia limitów. Retencja artefaktu wynosi tylko 1 dzień. [Zasady rozliczania GitHub Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

`config/cloud.json` zawiera wyłączony przykład przyszłego cron. **Nie ma aktywnego harmonogramu.** Ewentualne włączenie wymaga osobnej decyzji, trwałego prywatnego stanu, sprawdzenia limitów Overpass i zmiany zarówno triggera, jak i warunku joba. Kod nie uruchamia wysyłki, demonstracji ani publikacji stron klientów.

## Testy

```sh
python -m unittest discover -s prospect-finder/tests -v
node prospect-finder/tests/panel.test.mjs
npm --prefix demo-generator test
```

Testy sprawdzają kontrakt i składnię workflow (JSON będący YAML), ręczny trigger, parametry, uprawnienia i przypięte akcje, brak jawnych artefaktów, szyfrowanie/odszyfrowanie i zły klucz, bezpieczne odtwarzanie archiwum, backup SQLite/cache, prywatność magazynu i SHA lease, dwa przebiegi ze stanem i deduplikacją, liczniki raportu, brak sekretów i danych firm w Summary. Odpowiedzi GitHub i firmy w testach są syntetyczne; testy nie wykonują płatnych ani rzeczywistych operacji magazynu.

Do uruchomienia w Actions potrzebna jest opisana konfiguracja panelu GitHub. Integracja dostępna w sesji nie ma narzędzia do `workflow_dispatch`, a domyślna gałąź źródła pozostaje nienaruszona. Nie deklaruj sukcesu chmury ani znalezienia rzeczywistych firm przed sprawdzeniem rzeczywistego runu.

## Analiza pierwszego runu i ponowna próba

Sprawdzono [rzeczywisty run 40602920321](https://github.com/Yormiii/webforge-prospect-runner/actions/runs/40602920321), job `discover` (122535255016). 62 testy przeszły. Krok discovery trwał około 83 s (23:33:33–23:34:56 UTC), zgłosił 3 próby HTTP, 0 rzeczywistych firm i `discovery_blocked_or_failed`; artefakt został przesłany. Testowe wpisy „1 firma / completed” w starym Summary należy zignorować. Nie dowodzą pozyskania firmy.

Błąd izolacji był w kodzie: `run_cloud()` czytał odziedziczone `GITHUB_STEP_SUMMARY` także przy wstrzykniętym syntetycznym discovery. Teraz funkcja biblioteczna domyślnie nie zapisuje do Summary. Tylko produkcyjna komenda CLI jawnie przekazuje ścieżkę. Testy izolują też zmienne sekretów i Summary do własnego katalogu, a nowy workflow dodatkowo zeruje tę zmienną dla procesu testowego. Pełny zestaw testów został sprawdzony z odziedziczonym plikiem kontrolnym Summary: zawartość pozostała niezmieniona.

**Przyczyna błędu źródła nie jest jeszcze potwierdzona.** Stary publiczny raport nie zachował kategorii/statusu/czasów poszczególnych prób; surowy błąd pozostaje w szyfrowanym raporcie właściciela. Trzy próby odpowiadają ponowieniom błędów transportu lub HTTP 429/500/502/503/504; stary kod ponawiał także błąd limitu treści. Sam brak DNS przy wstępnej walidacji dałby 0 prób, a HTTP 200 z `remark` albo niepoprawnym JSON zwykle 1. Czas około 83 s jest zgodny m.in. z kilkukrotnym timeoutem wykonania/odpowiedzią gateway, lecz nie dowodzi HTTP 504. Nie ustalono awarii Overpass na podstawie lokalnej blokady DNS tego środowiska.

Zapytanie `all` zostało uproszczone bez zmiany znaczenia reguł: **37 → 8 klauzul przestrzennych, 2691 → 901 bajtów**. Nadal jedno zapytanie, 30 branż, 30 km dla Poznania, 25 s czasu serwera, 64 MiB pamięci, maksymalnie 1500 obiektów i 8 MiB pobierania. Retry/backoff, Retry-After, cache i limity nie zostały zwiększone. Nie ponawiamy deterministycznego przekroczenia wielkości odpowiedzi ani nieobsługiwanego kodowania, żeby nie pobierać trzykrotnie tej samej treści. To optymalizacja obciążenia, nie potwierdzona naprawa przyczyny historycznego runu.

Nowe Summary pokazuje kategorię przerwania i tabelę: zakres `overpass`/`website`, zdarzenie `response`/`error`/`cache`, kategorię, HTTP jeśli uzyskano odpowiedź, numer próby, czas w ms i liczbę bajtów jeśli odczyt się zakończył. Osobno pokazuje tylko liczbowy rozmiar zapytania, liczbę klauzul, promień i limit obiektów. Próba 0 oznacza np. błąd DNS przed HTTP, cache nie oznacza nowego żądania. Licznik „Próby HTTP” oznacza rezerwacje prób transportu, nie liczbę potwierdzonych odpowiedzi.

| Kategoria | Znaczenie i następny krok |
|---|---|
| `dns_error` | Resolver nie rozpoznał publicznego adresu; sprawdź sieć środowiska. |
| `timeout` | Timeout klienta/transportu; nie jest automatycznie dowodem ciężkiego zapytania. |
| `http_429` | Limit współdzielonego serwera; respektuj Retry-After i zaczekaj. |
| `http_5xx` | Błąd serwera/gateway; konkretny status jest w tabeli, spróbuj później pojedynczym przebiegiem. |
| `overpass_timeout` / `overpass_memory_limit` | HTTP 200 z komunikatem wykonania Overpass; nie importujemy częściowych danych. |
| `response_too_large` | Przekroczono limit klienta; bez automatycznego ponawiania i zwiększania limitu. |
| `tls_error` / `proxy_error` / `connection_error` | Błąd TLS, HTTP 407 lub połączenia; nie wyłączaj weryfikacji TLS/proxy. |
| `invalid_json` / `invalid_payload` / `overpass_runtime_error` | Nieprawidłowa lub niepełna odpowiedź; brak importu i wymyślonych wyników. |
| `budget_exceeded` / `retry_after_deferred` | Budżet albo odroczenie; poczekaj, nie resetuj stanu ani nie zmieniaj serwera w celu obejścia limitu. |
| `network_other` | Niejednoznaczny błąd transportu; szczegóły tylko w prywatnym raporcie. |

Dopuszczone są wyłącznie ustalone kody i ograniczone liczby. Tabela nie zawiera firm, identyfikatorów OSM, hostów stron firm, kontaktów, URL, nagłówków, treści odpowiedzi, wyjątków ani wartości sekretów. Testy sprawdzają odrzucanie takich pól. Diagnostyka obejmuje także nieudane i odczytane z cache odpowiedzi.

**Ponowny test w panelu GitHub:**

1. W `webforge-prospect-runner` zaktualizuj `.github/workflows/prospect-finder.yml` treścią [aktualnego szablonu z feature](https://github.com/Yormiii/Moja-strona/blob/feature/demo-generator/prospect-finder/workflow/prospect-finder.yml). Zatwierdź w prywatnym repozytorium sterującym. Nie zmieniaj `main` w `Moja-strona`. Aktualizacja dodaje dodatkową izolację procesu testowego; sama naprawa biblioteki i diagnostyka są pobierane z feature także przez dotychczasowy workflow.
2. Otwórz **Actions → WebForge Prospect Finder (manual) → Run workflow** i utwórz **nowy przebieg**, zamiast używać starego Summary. Pozostaw gałąź domyślną prywatnego runnera.
3. Ustaw `region=poznan`, `industry=all`, `limit=25`, `category=wszystkie`. Zachowaj istniejący sekret i wybrany tryb magazynu. Dla `private-repository` zachowaj repozytorium stanu i token; `temporary` nie zachowuje deduplikacji i budżetów między przebiegami. Nie przełączaj na temporary w celu pominięcia limitu trwałego stanu.
4. Kliknij **Run workflow**. W kroku testów powinny przejść **73 testy Python**, a Summary zawierać jeden raport właściwego wyszukiwania. Sprawdź checkout aktualnego commita gałęzi w logu. Nie powtarzaj wielu runów pod rząd przy 429/Retry-After.
5. Jeśli błąd wróci, odczytaj kategorię, HTTP i czasy z nowego Summary. Można udostępnić te kontrolowane liczby bez wysyłania odszyfrowanej bazy, kontaktów ani klucza. Jeśli trzeba porównać obciążenie, w późniejszej pojedynczej próbie wybierz np. `industry=mechanik`; sam mniejszy limit firm nie zmniejsza zapytania źródłowego (limit jest stosowany przy próbkowaniu odpowiedzi).

Nie uruchomiono ponownie workflow w imieniu użytkownika. Lokalna rzeczywista próba poprawionej wersji: **0 firm / 0 prób HTTP / `dns_error`**. Jest to ograniczenie tego wykonawcy, a nie wynik nowego przebiegu GitHub Actions. Testy używają wyłącznie syntetycznych odpowiedzi i nie potwierdzają dostępności Overpass ani pozyskania 20–30 firm.
