# AUDYT WEBFORGE — analiza projektu i wspólny dziennik pracy

- Repozytorium: [Yormiii/Moja-strona](https://github.com/Yormiii/Moja-strona).
- Analizowana gałąź: `main`.
- Commit będący podstawą audytu: `7a53aad3a3252cdeaafd6783eea392644391329e` (`7a53aad`), z 19 lipca 2026 r., komunikat „Add files via upload”.
- Data analizy i utworzenia dziennika: 27 października 2026 r.
- Status audytu bazowego: audyt i plan; w chwili jego wykonania poprawki, generator oraz migracja hostingu nie były wdrożone. Aktualny stan realizacji opisuje dziennik poniżej.
- Zakres: odczyt wszystkich plików tekstowych, pełnej struktury repozytorium, konfiguracji formularzy i historii wdrożeń; porównanie demonstracji i sprawdzenie lokalnych odnośników.
- Nie przeprowadzono testowego wysłania formularzy. Nie potwierdzono bieżącego DNS ani działania domeny w przeglądarce. Analiza kodu nie zastępuje testów wizualnych i testu doręczenia poczty.

## Zasady wspólnego dziennika i zakres upoważnienia

Na polecenie właściciela projektu ten plik jest wspólnym dziennikiem pracy nad WebForge.

1. Po każdym kolejnym zadaniu aktualizować ten dokument o wykonane działania, wyniki, napotkane problemy i następne kroki.
2. Zachować ustalenia audytu oraz historię; przy zmianie stanu oznaczać, co rozwiązano, zamiast usuwać kontekst.
3. Oddzielać ustalone fakty, nieweryfikowane informacje, rekomendacje i faktycznie wykonane prace.
4. Nie zmieniać innych plików projektu bez zgody użytkownika. Zgoda na prowadzenie dziennika nie jest zgodą na wdrażanie opisanych rekomendacji.
5. Nie dodawać do publicznego repozytorium sekretów, prywatnych danych potencjalnych klientów, wewnętrznych notatek handlowych ani danych dostępowych.
6. Niniejsze zadanie upoważnia do utworzenia i opublikowania wyłącznie `AUDYT_WEBFORGE.md`, najlepiej bezpośrednio na `main`.
7. Aktualizacja zakresu — Zadanie 1 (2026-10-27): użytkownik zezwolił na dodanie generatora, przykładów, instrukcji i testów oraz aktualizację audytu wyłącznie na `feature/demo-generator`. Nie zmieniać `main`, istniejących stron, formularzy ani plików produkcyjnych. Nie publikować na domenie, nie konfigurować płatnych usług, nie tworzyć PR i nie scalać gałęzi. To nowsze polecenie zastępuje zakres z punktu 6 dla tego zadania.

## Główna rekomendacja

**Najprostsze rozwiązanie to generator statycznych stron: obecny szablon HTML + dane firmy w JSON → gotowe demo pod osobnym adresem.** Nie potrzeba WordPressa, bazy danych ani płatnego kreatora. Hosting generatora i demonstracji może kosztować **0 zł miesięcznie** przy niewielkiej skali.

Rekomendowany zestaw: **obecny wygląd + wspólny szablon + JSON + mały generator Node.js + Cloudflare Pages Free**. Pozwala zacząć z dodatkowymi kosztami infrastruktury bliskimi zeru, a wygodny panel i AI dołożyć dopiero wtedy, gdy liczba demonstracji uzasadni ich budowę.

W trakcie samego audytu niczego nie zmieniano ani nie publikowano. Późniejsze utworzenie tego dokumentu jest osobnym, wyraźnie autoryzowanym zadaniem.

## 1. Struktura projektu i technologie

Repozytorium w analizowanym commicie zawiera 16 plików, wszystkie w głównym katalogu. Liczba ta nie obejmuje dodawanego później pliku audytu.

| Pliki | Rola |
|---|---|
| `index.html` | Strona główna WebForge |
| Osiem plików `demo-*.html` | Demonstracje branżowe |
| `dziekujemy.html` | Potwierdzenie po wysłaniu formularza |
| `polityka-prywatnosci-gotowa.html` | Polityka prywatności |
| `favicon.png`, `webforge-logo.png` | Grafiki |
| `CNAME` | Domena `webforge.com.pl` |
| `robots.txt`, `sitemap.xml` | Konfiguracja indeksowania |

### Technologie i działanie

- Zwykły **HTML i CSS**, ze stylami wewnątrz każdego pliku.
- Niewielki JavaScript na stronie głównej: animacje podczas przewijania przez `IntersectionObserver`.
- Responsywność przez CSS Grid, Flexbox i media queries.
- Formularze obsługuje zewnętrzny **FormSubmit**.
- Brak Reacta, frameworka, backendu, bazy danych, zależności npm oraz własnego procesu budowania.
- W analizowanym drzewie nie ma własnych plików workflow w `.github/workflows`.
- `robots.txt` dopuszcza indeksowanie całej witryny i wskazuje mapę strony.
- `sitemap.xml` zawiera wyłącznie adres strony głównej.
- Strona podziękowania ma `noindex`; obecne demonstracje nie mają takiego oznaczenia.

To lekki projekt, który dobrze nadaje się do automatycznego generowania kolejnych stron. Główna trudność przy rozbudowie to kopiowanie tego samego kodu między plikami.

Źródło: [pliki projektu](https://github.com/Yormiii/Moja-strona/tree/main).

## 2. Strony demonstracyjne i możliwość użycia ich jako szablonów

**Na stronie głównej pokazane są trzy dema, ale w repozytorium jest osiem.**

### Trzy demonstracje pokazane w portfolio

| Demo | Plik | Charakterystyka |
|---|---|---|
| AutoPro Serwis | `demo-mechanik.html` | Warsztat, pomarańczowe akcenty, cztery usługi |
| North Cut Barber | `demo-barber.html` | Barber, złote akcenty, cztery usługi |
| Studio Lumière | `demo-stylistka.html` | Beauty, różowe akcenty, cztery usługi |

### Wszystkie warianty branżowe

| Plik | Nazwa demonstracyjna | Branża | Przykładowe usługi |
|---|---|---|---|
| `demo-mechanik.html` | AutoPro Serwis | Warsztat samochodowy | Diagnostyka komputerowa, wymiana oleju i filtrów, hamulce i zawieszenie, klimatyzacja |
| `demo-barber.html` | North Cut Barber | Barbershop | Strzyżenie męskie, broda i kontur, pakiet włosy + broda, golenie brzytwą |
| `demo-stylistka.html` | Studio Lumière | Beauty | Stylizacja paznokci, brwi i rzęsy, makijaż okazjonalny, pakiety ślubne |
| `demo-elektryk.html` | VoltPro | Elektryk | Nowe instalacje, pomiary elektryczne, modernizacje rozdzielni, usuwanie usterek |
| `demo-hydraulik.html` | HydroFix 24 | Usługi hydrauliczne | Usuwanie awarii, montaż armatury, instalacje wodne, udrażnianie odpływów |
| `demo-kancelaria.html` | Kancelaria Lexum | Usługi prawne | Prawo cywilne, obsługa firm, umowy i dokumenty, konsultacje prawne |
| `demo-restauracja.html` | Bistro Verde | Restauracja | Menu sezonowe, lunch dnia, przyjęcia rodzinne, catering |
| `demo-trener.html` | Forma Studio | Trener personalny | Trening personalny, plan treningowy, analiza postępów, trening online |

Pięć pozostałych wariantów nie jest obecnie podlinkowanych z portfolio.

### Wspólna konstrukcja

Wszystkie osiem demonstracji ma wspólny układ:

1. Pasek powrotu do WebForge.
2. Nawigacja i sekcja otwierająca.
3. Cztery usługi.
4. Sekcje „Dlaczego my” oraz „Jak to działa”.
5. Przykładowa galeria.
6. Sekcja kontaktowa i stopka.

Porównanie kodu wykazało, że **CSS wszystkich demonstracji jest identyczny poza wartościami zmiennych kolorystycznych**. Różnice dotyczą głównie nazwy firmy, branży, nagłówka, usług i krótkich opisów.

### Co rzeczywiście działa

- Nawigacja przewija stronę do sekcji.
- Układ dopasowuje się do szerokości ekranu.
- Link powrotu prowadzi do portfolio WebForge.
- Końcowy przycisk prowadzi do formularza na stronie WebForge.
- Demonstracje są samodzielnymi stronami HTML, bez skryptów i formularzy.
- Statyczna kontrola odnośników lokalnych w ośmiu demonstracjach nie wykazała brakujących plików przy obecnym położeniu stron.

### Co jest tylko demonstracją

- Nie ma systemu rezerwacji, kalendarza ani formularzy w samych demach.
- „Galerie” to kolorowe bloki z napisami, bez zdjęć; demonstracje nie zawierają elementów `img`.
- Przyciski „Zarezerwuj termin” lub „Umów wizytę” przewijają do sekcji kontaktowej.
- Brakuje rzeczywistych danych kontaktowych prezentowanej firmy.
- Końcowy przycisk kieruje do WebForge, a nie do rzeczywistej firmy.

Opisy portfolio obiecują miejscami więcej niż realizują demonstracje: np. mapę, telefon, cennik czy formularz rezerwacji. Warto ujednolicić opisy z faktyczną funkcjonalnością.

### Przydatność jako szablony

**Można wykorzystać je jako szablony.** Najlepiej wyodrębnić jeden wspólny szablon i osiem zestawów danych branżowych. Na start wystarczy personalizacja nazwy firmy, miasta, kolorów, usług, tekstów, logo i zdjęć.

Źródła: [demo warsztatu](https://github.com/Yormiii/Moja-strona/blob/main/demo-mechanik.html), [demo barbera](https://github.com/Yormiii/Moja-strona/blob/main/demo-barber.html), [demo beauty](https://github.com/Yormiii/Moja-strona/blob/main/demo-stylistka.html).

## 3. Formularz kontaktowy i formularz opinii

Na stronie głównej są **dwa formularze**: zapytania ofertowego i opinii. Oba wysyłają zwykły HTTP POST do:

`https://formsubmit.co/kontakt@webforge.com.pl`

Przepływ:

**Użytkownik → FormSubmit → e-mail WebForge → strona podziękowania.**

### Formularz ofertowy

Formularz `quoteForm` przekazuje:

- imię lub nazwę firmy,
- opcjonalny telefon,
- e-mail,
- rodzaj strony,
- budżet,
- opis projektu,
- zaznaczenie zgody na kontakt.

Pola imienia/nazwy firmy, e-maila, opisu projektu i zgody są wymagane w HTML. Telefon jest opcjonalny.

Konfiguracja obejmuje:

- pole pułapkę `_honey`,
- włączoną CAPTCHA: `_captcha=true`,
- temat „Nowe zapytanie ze strony WebForge”,
- tabelaryczny format e-maila: `_template=table`,
- przekierowanie `_next` na `https://webforge.com.pl/dziekujemy.html`.

Formularz działa bez własnego JavaScriptu i backendu.

### Formularz opinii

Formularz `reviewForm` przekazuje autora, e-mail do weryfikacji, ocenę i treść opinii. Używa tego samego adresu FormSubmit, pola pułapki, CAPTCHA i formatu tabeli. Ma osobny temat „Nowa opinia o WebForge” oraz przekierowanie na `dziekujemy.html?typ=opinia`.

**Wysyła wiadomość e-mail — nie publikuje opinii automatycznie.** Strona opisuje ręczną weryfikację i zgodę autora przed publikacją. W repozytorium nie ma systemu zapisu opinii ani panelu administracyjnego.

### Aktywacja i ograniczenia weryfikacji

FormSubmit wymaga potwierdzenia adresu odbiorcy podczas pierwszego uruchomienia. **Z repozytorium nie można potwierdzić, czy aktywacja została wykonana i czy wiadomości faktycznie docierają.**

Nie wysyłano formularzy testowych. Nie zweryfikowano dostępu do skrzynki `kontakt@webforge.com.pl`, filtrów antyspamowych ani końcowego doręczenia.

`dziekujemy.html` jest statyczną stroną. Jej otwarcie samo w sobie nie potwierdza doręczenia wiadomości do skrzynki.

### Znaleziony błąd

**Formularz i stopka wskazują `polityka-prywatnosci.html`, a istniejący plik nazywa się `polityka-prywatnosci-gotowa.html`.** W analizowanym repozytorium brakuje pliku docelowego wskazanego odnośnikiem.

### Rekomendacja

Najtaniej pozostawić FormSubmit, poprawić odnośnik i później wykonać kontrolowany test obu formularzy. Zmiana kodu i testowe wysyłki nie zostały wykonane w ramach audytu.

Źródła: [kod formularzy](https://github.com/Yormiii/Moja-strona/blob/main/index.html), [istniejąca polityka prywatności](https://github.com/Yormiii/Moja-strona/blob/main/polityka-prywatnosci-gotowa.html), [strona podziękowania](https://github.com/Yormiii/Moja-strona/blob/main/dziekujemy.html), [dokumentacja FormSubmit](https://formsubmit.co/).

## 4. Wdrożenie i hosting

### Potwierdzone ustalenia

**Potwierdzono wdrażanie przez GitHub Pages.**

Dowody:

- `CNAME` zawiera `webforge.com.pl`.
- Ostatni znaleziony przebieg `pages build and deployment` zakończył się sukcesem 19 lipca 2026 r.
- Wdrożenie dotyczy commita `7a53aad3a3252cdeaafd6783eea392644391329e`, który był również aktualnym commitem `main` podczas audytu.
- Przebieg o identyfikatorze `29697014262` rozpoczął się o 17:32:03 UTC i zakończył o 17:33:03 UTC.
- Ścieżka `dynamic/pages/pages-build-deployment` wskazuje na wbudowany mechanizm GitHub Pages; własnego workflow w repozytorium nie ma.
- Gałąź przebiegu to `main`; witryna jest przechowywana jako pliki w katalogu głównym.

Źródła: [udane wdrożenie](https://github.com/Yormiii/Moja-strona/actions/runs/29697014262), [konfiguracja domeny](https://github.com/Yormiii/Moja-strona/blob/main/CNAME).

### Czego nie potwierdzono

To potwierdza platformę ostatniego wdrożenia. **Nie potwierdzono bieżącej konfiguracji DNS ani dostępności domeny** — narzędzie przeglądania nie zdołało otworzyć strony głównej ani sprawdzanych adresów demonstracji i polityki. Nie jest to wystarczający dowód, że strona nie działa.

Nie można też ustalić z tych plików dostawcy poczty ani rejestratora domeny. Odczyt kolekcji wdrożeń przez użyte narzędzie GitHub był niedostępny; ustalenie dotyczące hostingu oparto na dostępnym przebiegu GitHub Actions, a nie na tej kolekcji.

### Rekomendacja hostingowa

Przy rozwoju systemu demonstracji rekomendowany jest **Cloudflare Pages**.

GitHub opisuje ograniczenia używania Pages do prowadzenia biznesu i obsługi transakcji komercyjnych, dlatego nie należy opierać na nim docelowego systemu sprzedażowych demonstracji. To rekomendacja dotycząca dalszej architektury, a nie potwierdzenie naruszenia zasad przez obecną witrynę.

Źródło: [zasady GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).

## 5. Proponowany system automatycznego generowania indywidualnych demo

### Zakres najprostszej wersji

Rekomendowany jest **jeden generator uruchamiany podczas budowania strony**, wykorzystujący obecne HTML i CSS.

Przebieg:

**Wpisujesz dane firmy → wybierasz branżę → generator tworzy HTML → hosting publikuje demo → otrzymujesz link.**

Przykładowy adres:

`https://demo.webforge.com.pl/autoserwis-kowalski-a7k2/`

Jest to adres planowany, nie istniejące wdrożenie potwierdzone podczas audytu.

Jedna subdomena i jeden projekt hostingowy obsłużą wiele demonstracji. Nie potrzeba osobnej domeny ani oddzielnego wdrożenia dla każdego klienta.

### Proponowana struktura nowych plików

```text
templates/demo.html         wspólny szablon
data/industries.json        warianty branżowe
data/clients/*.json         dane poszczególnych firm
scripts/build.mjs          generator w Node.js
dist/                      wynik gotowy do publikacji
```

To planowane pliki; ich utworzenie wymaga osobnej zgody użytkownika.

### Obowiązki generatora

Generator powinien:

- wstawiać nazwę, miasto, usługi, kolory i materiały firmy;
- bezpiecznie kodować treści oraz sprawdzać adresy linków;
- tworzyć unikalny adres każdej demonstracji;
- poprawnie ustawiać odnośniki do WebForge — obecne względne `index.html#kontakt` wymaga zmiany przy zagnieżdżonych adresach;
- dodawać oznaczenie „Propozycja strony przygotowana przez WebForge”;
- ustawiać `noindex` i pomijać indywidualne dema w sitemapie;
- umożliwiać wyłączenie demonstracji przez zmianę jej statusu w danych.

### Dane i prywatność

**`noindex` ogranicza indeksowanie, ale nie zapewnia prywatności.**

Ponieważ obecne repozytorium jest publiczne, nie należy umieszczać w nim wewnętrznych notatek, budżetów ani prywatnych danych kontaktowych potencjalnych klientów. Sam trudny do odgadnięcia adres także nie zastępuje kontroli dostępu.

Na początku dane można dodawać przez edytor GitHub. Automatyczne będzie tworzenie i publikowanie stron; zbieranie informacji o firmach pozostanie ręczne. To najprostszy zakres, który daje realną oszczędność pracy.

### Rola AI

AI można dodać później wyłącznie do przygotowywania propozycji tekstów. Nie powinno samodzielnie wymyślać opinii, kwalifikacji, cen czy doświadczenia firmy. Do pierwszej wersji API AI nie jest potrzebne.

### Hosting generatora i demonstracji

Najpierw uruchomić osobny projekt demonstracji na `demo.webforge.com.pl`. Migrację głównej witryny przeprowadzić osobno po sprawdzeniu podglądu.

Cloudflare obsługuje zwykły HTML oraz automatyczne budowanie po zmianach w GitHub. Generator ma tworzyć katalog `dist/`, a hosting publikować jego zawartość. Nie jest potrzebny działający stale serwer generatora ani baza danych.

Źródła: [obsługa HTML](https://developers.cloudflare.com/pages/framework-guides/deploy-anything/), [integracja GitHub](https://developers.cloudflare.com/pages/configuration/git-integration/).

## 6. Konkretny plan wdrożenia

| Etap | Zakres | Szacowany czas |
|---|---|---:|
| 1. Uporządkowanie | Link polityki, opisy portfolio, sprawdzenie formularzy | 1–2 godz. |
| 2. Szablon | Wspólny HTML/CSS i osiem wariantów branżowych | 3–5 godz. |
| 3. Generator | Dane JSON, walidacja, adresy, zdjęcia, status demonstracji | 4–6 godz. |
| 4. Hosting | Podłączenie repozytorium do Cloudflare Pages, budowanie `dist/`, subdomena demo | 1–3 godz. |
| 5. Weryfikacja | Trzy przykładowe firmy, widok mobilny, linki, indeksowanie i formularze | 2–4 godz. |

**Łącznie: około 11–20 godzin pracy**, zależnie od jakości materiałów i zakresu personalizacji. To szacunek, nie wycena wykonawcy.

Plan jest propozycją. Żaden z tych etapów nie został wykonany w ramach audytu ani samego zapisania dokumentacji.

## 7. Orientacyjne koszty

Dla kilkudziesięciu lub kilkuset lekkich demonstracji:

| Element | Koszt |
|---|---:|
| Generator Node.js | 0 zł opłat za oprogramowanie |
| Cloudflare Pages Free i HTTPS | 0 zł/mies. w limitach planu |
| FormSubmit | 0 zł według oferty sprawdzonej podczas audytu |
| Baza danych | Niepotrzebna |
| API AI | 0 zł — niepotrzebne w pierwszej wersji |
| Subdomena `demo.webforge.com.pl` | Zwykle bez dodatkowej opłaty |
| Odnowienie obecnej domeny | Według obecnego rejestratora; budżetowo ok. 60–150 zł/rok |
| Obecna skrzynka e-mail | Według obecnego dostawcy; koszt nieustalony |

Cloudflare Pages Free ma według dokumentacji sprawdzonej podczas audytu limit **500 buildów miesięcznie i 20 000 plików na stronę**. Jedno budowanie może wygenerować wszystkie dema naraz. Przy większych paczkach warto dodawać wiele firm w jednej zmianie.

Źródła: [limity Cloudflare](https://developers.cloudflare.com/pages/platform/limits/), [Cloudflare Pages](https://www.cloudflare.com/products/pages/), [FormSubmit](https://formsubmit.co/).

Przy zleceniu wdrożenia i przykładowej stawce 100–200 zł/h jednorazowy koszt wyniósłby orientacyjnie **1100–4000 zł**, bez zakupu zdjęć, pisania indywidualnych tekstów i ewentualnego VAT.

Kwota 0 zł/mies. dotyczy dodatkowej infrastruktury najprostszej wersji w darmowych limitach. Nie obejmuje pracy człowieka, obecnej poczty, odnowienia domeny ani płatnych materiałów. Widełki domeny są założeniem budżetowym, a nie ustaloną fakturą lub ofertą obecnego rejestratora. Ceny i limity należy ponownie sprawdzić przed wdrożeniem.

## 8. Rejestr problemów i otwartych kwestii

| ID | Ustalenie lub problem | Status | Zalecane następne działanie |
|---|---|---|---|
| P-01 | Linki do `polityka-prywatnosci.html` nie odpowiadają istniejącej nazwie pliku | Otwarte | Po zgodzie poprawić ścieżkę albo nazwę pliku i sprawdzić oba odnośniki |
| P-02 | Opisy trzech pozycji portfolio wymieniają funkcje nieobecne w demonstracjach | Otwarte | Ujednolicić opisy z demonstracjami albo osobno uzgodnić dodanie funkcji |
| P-03 | Powielony HTML/CSS w ośmiu demonstracjach | Otwarte | Wydzielić wspólny szablon i dane branżowe |
| P-04 | Brak potwierdzenia aktywacji FormSubmit i doręczenia poczty | Niezweryfikowane | Kontrolowany test formularza zapytania i opinii oraz sprawdzenie skrzynki |
| P-05 | Otwarcie strony podziękowania nie jest dowodem doręczenia e-maila | Ograniczenie obecnej konstrukcji | Weryfikować dostarczenie po stronie odbiorcy |
| P-06 | Nie potwierdzono aktualnego DNS i dostępności domeny | Niezweryfikowane | Sprawdzić DNS, HTTPS i odpowiedzi serwera; błąd narzędzia nie dowodzi awarii |
| P-07 | Rejestrator domeny, dostawca poczty i rzeczywiste koszty są nieznane | Niezweryfikowane | Ustalić na podstawie paneli lub dokumentów właściciela |
| P-08 | Względne powroty do WebForge przestaną wskazywać właściwe miejsce po przeniesieniu demo do podkatalogów/subdomeny | Do uwzględnienia w generatorze | Stosować poprawne docelowe adresy WebForge |
| P-09 | Indywidualne demo i dane w publicznym repozytorium nie są prywatne | Wymóg projektowy | Ograniczyć dane publikowane; `noindex` nie traktować jako zabezpieczenia |
| P-10 | GitHub Pages ma ograniczenia zastosowań biznesowych | Rekomendacja architektoniczna | Docelowy system demonstracji oprzeć na Cloudflare Pages |
| P-11 | Brak generatora, panelu i integracji AI | Planowane, niewdrożone | Zacząć od generatora JSON → HTML; panel i AI rozważyć później |
| P-12 | Pięć dodatkowych wariantów nie jest pokazanych w portfolio | Ustalenie | Można wykorzystać w generatorze; ewentualna zmiana portfolio wymaga zgody |

## 9. Dziennik pracy

### 2026-10-27 — sprawdzenie dostępu do repozytorium

**Wykonane działania:**

- Odczytano metadane repozytorium `Yormiii/Moja-strona`.
- Potwierdzono dostęp do gałęzi `main`, listy plików i fragmentu `index.html`.
- Potwierdzono, że odczytany plik dotyczy projektu WebForge.

**Wyniki:** dostęp do repozytorium i odczyt plików działają.

**Problemy:** nie napotkano przeszkód w odczycie przez połączenie GitHub.

**Następne kroki:** szczegółowa analiza projektu zgodnie z kolejnym poleceniem użytkownika.

**Zakres zmian:** brak zmian w repozytorium.

### 2026-10-27 — szczegółowy audyt gałęzi main

**Wykonane działania:**

- Odczytano pełne drzewo `main` i wszystkie pliki tekstowe.
- Przeanalizowano stronę główną, osiem demonstracji, oba formularze, politykę prywatności, stronę podziękowania, `CNAME`, `robots.txt` i `sitemap.xml`.
- Porównano CSS demonstracji; potwierdzono wspólny kod poza zmiennymi kolorystycznymi.
- Sprawdzono odnośniki lokalne i wykryto brak pliku wskazywanego przez link polityki prywatności.
- Odczytano historię GitHub Actions i znaleziono udane wdrożenie aktualnego commita przez GitHub Pages.
- Podjęto próbę odczytu domeny narzędziem przeglądania.
- Sprawdzono oficjalne materiały FormSubmit, Cloudflare Pages i ograniczenia GitHub Pages.
- Przedstawiono plan generatora, plan wdrożenia oraz orientacyjne koszty.

**Wyniki:** pełne ustalenia, rekomendacje i plan znajdują się w sekcjach 1–8 tego dokumentu.

**Problemy i ograniczenia:**

- Narzędzie przeglądania nie uzyskało dostępu do domeny; nie ustalono przyczyny i nie stwierdzono na tej podstawie awarii witryny.
- Endpoint kolekcji wdrożeń nie był obsługiwany przez użyte narzędzie; dowód wdrożenia uzyskano z GitHub Actions.
- Nie wysłano formularzy i nie potwierdzono aktywacji ani końcowego doręczenia wiadomości.
- Nie ustalono dostawcy poczty, rejestratora domeny ani rzeczywistych opłat.

**Następne kroki:** zachowanie audytu w repozytorium; wdrożenie poprawek lub generatora dopiero w zakresie osobno zatwierdzonym przez użytkownika.

**Zakres zmian:** sam audyt był wyłącznie odczytem; nie zmieniono ani nie opublikowano plików projektu.

### 2026-10-27 — zapis audytu i ustanowienie wspólnego dziennika

**Polecenie użytkownika:** zapisać pełną przedstawioną analizę do `AUDYT_WEBFORGE.md`, utworzyć commit i opublikować go na GitHubie, najlepiej na `main`. Od tej pory prowadzić w tym pliku dziennik po każdym zadaniu. Nie zmieniać innych plików bez zgody.

**Wykonane działania objęte tym wpisem:**

- Ponownie odczytano drzewo gałęzi `main`; przed dodaniem dokumentu nadal wskazywało commit `7a53aad3a3252cdeaafd6783eea392644391329e`.
- Potwierdzono brak istniejącego `AUDYT_WEBFORGE.md`.
- Przygotowano niniejszy dokument zawierający całą przedstawioną analizę, wszystkie problemy, rekomendacje, plan automatyzacji, etapy wdrożenia i szacunkowe koszty.
- Dodano zasady prowadzenia wspólnego dziennika, rejestr otwartych kwestii i historię dotychczasowych zadań.

**Wynik zapisu:** przygotowano pełną treść dokumentu i zapisano ją lokalnie jako `/workspace/AUDYT_WEBFORGE.md`. Próba utworzenia pliku i commita bezpośrednio na `main` przez API GitHub została odrzucona. Nie utworzono commita ani nie opublikowano pliku w repozytorium. Żaden istniejący plik projektu nie został zmieniony.

**Problemy:**

- Na etapie przygotowania dokumentu nie stwierdzono konfliktu z istniejącym plikiem ani zmiany bazowego commita.
- Integracja GitHub zwróciła przy tworzeniu pliku błąd `403: Resource not accessible by integration`.
- Sprawdzono środowisko zgodnie z instrukcjami `cloud-environment-runtime`; nie wykazano skonfigurowanych dodatkowych poświadczeń zapisu.
- `gh auth status` zgłosiło nieważny token `GH_TOKEN`.
- Próba pobrania publicznego repozytorium przez Git zakończyła się brakiem połączenia z serwerem proxy na porcie 8080.
- Z powodu tych przeszkód nie było możliwe utworzenie i opublikowanie commita na GitHubie. To blokada techniczna, nie brak zgody użytkownika.

**Następne kroki:**

- Przywrócić działające połączenie GitHub z prawem zapisu zawartości do repozytorium `Yormiii/Moja-strona`.
- Po przywróceniu dostępu ponownie sprawdzić aktualną gałąź i ewentualne istnienie dokumentu, utworzyć commit obejmujący wyłącznie ten plik i opublikować go na `main`, jeśli zasady gałęzi na to pozwalają.
- Po publikacji zweryfikować treść pliku oraz potwierdzić, że commit obejmuje wyłącznie ten dokument.
- Po każdym następnym zadaniu dopisywać działania, wyniki, problemy i następne kroki.
- Oczekiwać kolejnego zadania użytkownika; poprawki kodu, generator, migracja i zmiany DNS pozostają niewdrożone i wymagają odrębnej zgody.

**Zakres zmian:** wyłącznie `AUDYT_WEBFORGE.md`; bez zmian HTML, CSS, formularzy, konfiguracji hostingu i domeny. Commit dokumentacji na `main` może uruchomić istniejący automatyczny proces GitHub Pages; nie jest to wdrożenie proponowanego generatora ani migracja.


### 2026-10-27 — Zadanie 1: pierwsza wersja generatora demonstracji

**Zgoda i zakres:** użytkownik zlecił generator, fikcyjny przykład, instrukcję i testy oraz aktualizację dziennika na osobnej gałęzi `feature/demo-generator`. Zabronił zmian `main`, istniejących stron, formularzy i innych plików produkcyjnych, wdrażania na domenę, płatnych usług, tworzenia PR i scalania.

**Stan początkowy i odczyt audytu:**

- Najpierw przeczytano lokalny audyt, następnie jego aktualną kopię z GitHub.
- Na GitHubie audyt jest już obecny: aktualny snapshot `main` to `8f07e41bdfad0d491b4d617c8a23a25a9465bb72`. Historyczny wpis o wcześniejszym nieudanym zapisie pozostawiono jako historię; opisuje poprzednią próbę, nie aktualny brak dokumentu.
- Odczytano wszystkie 17 plików tego snapshotu przez integrację GitHub. Lokalną bazę odtworzono z oryginalnych obiektów, sprawdzając SHA każdego pliku, drzewa i podpisanego commita. To płytka lokalna kopia Git, z tym samym commitem bazowym co GitHub.
- Utworzono lokalną gałąź `feature/demo-generator`; nie tworzono ani nie zmieniano lokalnej gałęzi `main`.

**Wykonane działania:**

- Dodano wyłącznie nowy katalog `demo-generator/` i zaktualizowano niniejszy audyt.
- `templates/demo.html`: wspólny układ i CSS bazujące na ośmiu istniejących demonstracjach; źródła produkcyjne pozostały nienaruszone.
- `data/industries.json`: etykiety, kolory i CTA ośmiu branż: mechanik, barber, stylistka, elektryk, hydraulik, kancelaria, restauracja i trener. Każdy profil wskazuje plik źródłowy.
- `generate.mjs`: generator Node.js bez zależności zewnętrznych. Czyta JSON z nazwą, branżą, miastem, usługami, opisem, kolorami i kontaktem; tworzy samodzielny HTML w `demo-generator/generated/<slug>/index.html`.
- Obsłużono 1–12 usług jako tekst lub obiekty z opisami, dane telefonu/e-maila/WWW/adresu, opcjonalne kolory branżowe, jawny lub automatyczny slug z obsługą polskich znaków i stabilnym skrótem.
- Dodano walidację wymaganych i nieznanych pól, kolorów, kontaktów i bezpiecznych adresów HTTP/HTTPS; kodowanie treści HTML; ochronę przed przejściem poza katalog wyników i symlinkami. Nadpisanie wymaga jawnego `--force`.
- Gotowe demo ma widoczne oznaczenie propozycji WebForge, `noindex, nofollow`, bezwzględne odnośniki do WebForge i prawidłowe kotwice sekcji. Nie zawiera skryptów, formularzy, systemu rezerwacji ani fikcyjnych opinii czy kwalifikacji.
- `examples/firma-testowa.json`: fikcyjna firma „Serwis Orbita TEST — firma fikcyjna”, Łódź, trzy usługi, własne kolory i wyłącznie fikcyjne dane kontaktowe (domeny `.invalid`, zerowy telefon).
- Wygenerowano i dołączono `generated/serwis-orbita-test/index.html`.
- Dodano `README.md` z uruchamianiem, schematem danych, listą branż, instrukcją podglądu, zakresem i ograniczeniami, oraz `package.json` ze skryptami bez instalowania pakietów.
- Dodano 13 testów opartych na wbudowanym `node:test`.

**Uruchamianie z katalogu głównego repozytorium:**

```sh
node demo-generator/generate.mjs demo-generator/examples/firma-testowa.json --force
node --test demo-generator/test/*.test.mjs
```

Do szczegółowego raportu wszystkich przypadków można również uruchomić `node demo-generator/test/generator.test.mjs`. W tym środowisku tryb `--test` raportował pojedynczy plik testowy jako zbiorczy wynik; bezpośrednie uruchomienie potwierdziło wszystkie 13 przypadków.

**Wyniki weryfikacji:**

- Node.js 24.19.0; deklarowane minimum projektu: Node.js 20. Nie wykonywano osobnego przebiegu na Node.js 20.
- **13/13 testów przeszło, 0 błędów.** Sprawdzono: zgodność ośmiu profili z demonstracjami źródłowymi, personalizację, kontakty, noindex i oznaczenie demo, kotwice i niezależność od lokalnych zasobów, brak formularzy/skryptów, XSS i jednokrotne podstawianie znaczników, błędne dane, protokoły URL, polskie znaki i rozróżnianie slugów, zapis i jawne odświeżanie, brak plików przy błędzie, symlinki, błędy CLI, generowanie z innego katalogu i odtwarzalność przykładu.
- `npm --prefix demo-generator test` oraz kontrola składni `node --check demo-generator/generate.mjs` zakończyły się powodzeniem.
- Wygenerowany HTML jest odtwarzalny z JSON; test porównuje go z dołączonym wynikiem.
- Kontrola Git potwierdziła brak zmian w istniejących plikach produkcyjnych. Zmiany obejmują tylko `AUDYT_WEBFORGE.md` i osiem nowych plików w `demo-generator/`.
- Próba podglądu mobilnego i desktopowego przez Playwright nie zakończyła się renderowaniem: brak przeglądarki w cache, a systemowy Chromium przerwał start z `setsockopt: Operation not permitted` / SIGTRAP. Nie potwierdzono wizualnie wyglądu ani braku poziomego przewijania. Nie przedstawiać tej próby jako zaliczonego testu wizualnego.

**GitHub, commit i ograniczenia:**

- Próba utworzenia zdalnej gałęzi `feature/demo-generator` z aktualnego `main` została odrzucona: `403 Resource not accessible by integration`. Zdalna gałąź nie została utworzona.
- Zwykłe klonowanie Git również nie zadziałało: brak połączenia z proxy na porcie 8080. Nie obchodzono proxy i nie zmieniano konfiguracji poświadczeń.
- Przygotowano lokalny commit na `feature/demo-generator` oraz eksport zmian jako ZIP i patch do zastosowania po przywróceniu zapisu. SHA lokalnego commita odczytać z `git log -1`; nie wpisuje się własnego SHA do treści tego samego commita.
- Nie wysłano zmian do GitHub, nie utworzono PR i nie scalono gałęzi. Brak działającego linku do zdalnej gałęzi.
- Nie uruchomiono wdrożenia, nie modyfikowano domeny, DNS, hostingu, formularzy, `CNAME`, sitemap ani produkcyjnych demonstracji. Nie skonfigurowano płatnych usług. Dodatkowy koszt wykonania generatora w tej wersji: brak opłat za API lub infrastrukturę.

**Stan wcześniejszych rekomendacji:**

- P-03: wspólny szablon i dane wyodrębniono dla nowego generatora; istniejące osiem stron zachowano bez refaktoryzacji.
- P-08: nowe demo używa bezwzględnych odnośników do WebForge.
- P-09: dodano oznaczenie i noindex; dane przykładu fikcyjne. Noindex nadal nie zapewnia prywatności.
- P-11: generator v0.1 działa lokalnie; panel, AI i automatyczne wdrożenie nadal nie są zaimplementowane.
- P-01, P-02 oraz pozostałe niezweryfikowane kwestie produkcyjne pozostają otwarte; nie poprawiano ich w tym zadaniu.

**Następne kroki:**

1. Przywrócić integracji GitHub prawo zapisu i utworzyć zdalne `feature/demo-generator`, publikując wyłącznie przygotowane zmiany (bez PR i bez modyfikacji `main`). Przed publikacją sprawdzić aktualny stan gałęzi i ewentualne równoległe zmiany; nie wymuszać nadpisania.
2. Sprawdzić wygenerowany przykład wizualnie w działającej przeglądarce na telefonie i komputerze oraz uzgodnić wygląd i kontrast.
3. W osobnym zadaniu rozważyć obsługę paczki wielu firm, statusów aktywne/wyłączone, zdjęć i wygodnego wprowadzania danych.
4. Hosting na osobnej subdomenie i automatyczne wdrożenie pozostają osobnym etapem wymagającym zgody.
5. Po następnym zadaniu ponownie uzupełnić dziennik; historyczne analizy zachować.

### 2026-10-27 — ponowienie publikacji po aktualizacji uprawnień GitHub

**Polecenie:** opublikować gotowy generator i audyt na `feature/demo-generator`, bez zmian `main` i bez Pull Requesta.

**Wykonane działania:**

- Odczytano dziennik, stan lokalnej gałęzi i commit generatora `0d154e03f10dcb0d8def6ad88aa0b54f5dbc996d`.
- Sprawdzono aktualny `main`: nadal `8f07e41bdfad0d491b4d617c8a23a25a9465bb72`. Nie było równoległych zmian wymagających scalenia.
- Sprawdzono listę gałęzi: `feature/demo-generator` jeszcze nie istniała.
- Po aktualizacji uprawnień udało się utworzyć zdalną gałąź `feature/demo-generator` z aktualnego `main`. Wcześniejszy błąd 403 dotyczący tej operacji nie wystąpił.
- Przygotowano zapis wszystkich ośmiu plików `demo-generator/` oraz niniejszego audytu przez GitHub API. Kod generatora i jego przykład nie wymagają zmian; wyniki wcześniejszych 13/13 testów pozostają aktualne.

**Stan tego wpisu:** gałąź istnieje, przygotowano commit z plikami; wynik zapisu i porównania zawartości będzie odnotowany w kolejnym wpisie po odczycie danych z GitHub.

**Problemy:** narzędzie odczytu nie przyjęło zakodowanego ukośnika w adresie pojedynczej gałęzi; jej nieistnienie potwierdzono przez listę gałęzi. Nie było to ograniczenie uprawnień zapisu.

**Następne kroki:** opublikować przygotowaną zawartość na nowej gałęzi, porównać wszystkie pliki z wersją lokalną, sprawdzić brak zmian produkcyjnych i niezmieniony SHA `main`, następnie dopisać wynik weryfikacji. Nie tworzyć PR, nie scalać i nie wdrażać na domenę.

### 2026-10-27 — publikacja generatora potwierdzona

**Wynik:** publikacja na GitHub zakończyła się powodzeniem. Gałąź: [feature/demo-generator](https://github.com/Yormiii/Moja-strona/tree/feature/demo-generator).

**Wykonane działania i weryfikacja:**

- Opublikowano komplet generatora oraz audyt w commicie [310e72f](https://github.com/Yormiii/Moja-strona/commit/310e72f8c7afe91effd0d22653587be62ef6410b).
- Ponownie odczytano z GitHub wszystkie 9 zmienionych/dodanych plików: ich pełna treść była identyczna z przygotowaną wersją lokalną.
- Porównanie gałęzi z bazowym `main` wykazało dokładnie osiem nowych plików `demo-generator/` i modyfikację `AUDYT_WEBFORGE.md`; żadnych zmian w plikach produkcyjnych.
- Odczyt listy gałęzi potwierdził, że `feature/demo-generator` wskazuje opublikowany commit, a `main` nadal wskazuje `8f07e41bdfad0d491b4d617c8a23a25a9465bb72`.
- Niniejszy wynik weryfikacji zapisano jako osobną aktualizację dziennika na tej samej gałęzi.
- Nie zmieniano kodu po wcześniejszym pomyślnym przebiegu 13/13 testów; nie powtarzano testów bez zmiany implementacji.
- Nie tworzono Pull Requesta, nie scalano gałęzi i nie publikowano generatora na domenie. Nie konfigurowano płatnych usług.

**Problemy:** wcześniejsza blokada 403 zapisu została rozwiązana przez aktualizację uprawnień. Ograniczenie podglądu wizualnego z poprzedniego zadania pozostaje otwarte.

**Następne kroki:** użytkownik może przeglądać i pobrać kod z gałęzi; następnie sprawdzić lokalnie wygląd demonstracji w przeglądarce i zlecić kolejny etap. PR, scalanie, wdrożenie i zmiany produkcyjne wymagają osobnego polecenia.
