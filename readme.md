LICENSES EXPORTER
=================

Abstract
--------

 Los diferentes servidores de licencias de software utilizan diferentes métodos/utilidades para recuperar información sobre el estado y el uso de las licencias. Los más habituales pueden ser:
- **Utilidad específica multiplataforma:** Como en el caso de las licencias FlexNet o Sentinel RMS entre otras. Se dispone de un ejecutable de línea de comandos que devuelve una información textual con los datos sobre las licencias.
- **Utilidad en windows:** Las licencias, mayoritariamente asociadas a aplicaciones exclusivamente windows, pueden disponer de una utilidad gráfica para la interrogación de su estado. Suelen ser sistemas de licencias propietarios del mismo fabricante de la aplicación.
- **Página web:** Cada vez más los servidores de licencias están proporcionando páginas web en el propio servidor que las alberga para dar la información.

LicensesExporter es una aplicación desarrollada en python que en base a un fichero yaml de configuración interroga secuencialmente los servidores de licencias, parsea la información extraida generando los objetos necesarios. Con ellos genera un endpoint para que prometheus pueda *scrapearlo* e introducir dicha información en su BBDD de series temporales. Dicha información podrá ser posteriormente tratada con terceras herramientas como grafana u otras.

La ventaja de usar prometheus para un sistema de este tipo es evidente. El recolector de datos (LicensesExporter) es pasivo y no introduce ninguna información en ningún backend de BBDD, generando simplemente una página web con toda la información sumarizada y sirviéndola el mismo desde su propio servicio web. Prometheus se dedica entonces como backend y recolector a scrapear y gestionar la persistencia según se configure. Del mismo modo la información generada por LicensesExporter puede ser scrapeada por cualquier otro sistema de monitorización alternativo.

El desarrollo de utilidades de monitorización basadas en este paradigma no requiere ningún privilegio especial por parte del desarrollador, ni en la fase de desarrollo y de pruebas generan información persistente que haya que purgar posteriormente de ninguna BBDD.

Conceptos y claves
------------------
- **Parser:** El módulo o sistema que se empleará para extraer la información de cada uno de los servidores de licencias.
- **App:** Se corresponde con una aplicación genérica cuyas licencias van a ser monitorizadas. Por ejemplo SPSS, Autocad, etc.
- **Feature:** Cada una de las características, módulos o ediciones de una aplicación susceptibles de ser licenciadas.
- **User:** En aquellos servidores de licencias que dan información sobre los usuarios activos, este objeto almacena la misma.
- **Escrapear:** Extraer de una página web información concreta.
-  **License server:** El FQDN del servidor que alberga un determinado servidor de licencias.
-  **Webdriver:** El interfaz para producir la salida de un navegador totalmente renderizado y poder escrapearlo.
-  **Selenium:** Un webdriver que permite la ejecución remota de navegadores en un servidor externo.

Parsers
-------
El parser a utilizar para cada licencia viene definido por la variable **type** del fichero de configuración. Los parsers desarrollados hasta el momento son:
- **lmutil:** Utiliza el ejecutable lmutil para interrogar servidores de licencias **FlexNet®**. Permite la interrogación de usuarios.
- **lsmon:** Utiliza el ejecutable lsmon para interrogar servidores de licencias **Sentinel RMS®**. Permite la interrogación de usuarios.
- **rlmutil:** Utiliza el ejecutable rlmutil para interrogar servidores de licencias **Reprise RLM®**. Permite la interrogación de usuarios.
- **Web:** Parser genérico para escrapping de páginas web donde  la información de licencias no tiene porqué estar en tablas. Se basa en busqueda de expresiones regulares. Soporta extracción de usuarios.
- **WebTable:** Parser web que escrapea tablas de páginas web. Utiliza DataFrames de pandas para extraer la información. Soporta extracción de usuarios.
- **WebTableJS:** Parser web que escrapea tablas de páginas web generadas mediante javascript. Utiliza selenium como webdriver y DataFrames de pandas para extraer la información. Soporta extracción de usuarios.
- **RawSocket:** Parser genérico que solo comprueba la existencia del servidor de licencias asociado a un puerto determinado. En principio no puede detectar ni caducidades, ni uso de licencias ni usuarios, pero si que la máquina y el servidor de licencias correspondiente están arrancados.
