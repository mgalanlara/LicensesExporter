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

Fichero de configuración
------------------------
El fichero de configuración se llama config.yml y tiene formato yaml. Tiene 3 secciones:
- **onlythis:** En ella se puede poner una lista de las App que se quiere que monitorize. Muy apropiado para desarrollo y corrección de errores.
- **licenses:** Dentro de ella hay una lista de Apps que se van a monitorizar, cada una con todos sus parámetros.
- **config:** Configuración general de la aplicación.

Configuración detallada y por tipo de parser
--------------------------------------------

### **Parámetros de la sección config** ###
- **port:** EL puerto tcp en el que LicensesExporter publicará los resultados (es una página web realmente), para que sean escrapeados por prometheus u otras herramientas.
- **sleep:** El número de segundos que transcurriran antes de hacer una nueva interrogación a las Apps.
- **lsmon_cmd, lmutil_cmd, rlmutil_cmd:** El path y argumentos de cada una de estas utilidades para los parsers.
- **webdriver:** Marca el inicio de la sección webdriver.
  - **type *(local/remote)*:** Si el navegador del webdriver se ejecutará en local (*chrome*) o remoto (*selenium*).
  - **private-url, public-url:** En el caso de webdriver remoto, si LicensesExporter se está ejecutando en un docker se usará private-url, public-url si se ejecuta fuera de un docker.

### **Parámetros comunes de la sección licenses** ###
- **name:** El nombre de la App.
- **type:** El tipo de parser.
- **skip *(True/False)*:** Si se debe evaluar o no.
- **license_server:** El FQDN del servidor de licencias. Puede ir en el formato *puerto*@*fqdn* para especificar el puerto tcp usado.
- **features:** Indica que comienza la sección de configuración de features.
- **users:** Indica que comienza la sección de configuración de usuarios.
- **used_as_free *(True/False)*:** Si las licencias que reporta el parser son las usadas o las que quedan libres. Por defecto asumimos que son las usadas.
- **product:** Si el parser reporta varios productos, en esta subsección se seleccionan.
  - **include:** La lista de los que queremos incluir.
  - **label:** La etiqueta que debemos buscar para identificar el producto.

### **Parámetros de la subsección licenses-features** ###
- **include:** La lista de los nombres de las features que queremos incluir. **ALL** si queremos incluir todas.
- **url:** *(para los parsers web, webtable y webtablejs)* Encabezado de la sub-subsección url.
  - **prefix:** El prefijo de la url.
  - **suffix:** El sufijo de la url.
  - **index:** La lista de índices que se usarán para formar las urls, o *null* si no hay suffix.
- **match:** *(para el parser web)* El encabezado de la sub-subsección de expresiones regulares para hacer matching.
  - **exist:** La regex para comprobar si el servidor de licencias y la licencia existe y está activa.
  - **total:** La regex que nos devolverá el número total de licencias disponibles.
  - **used:** La regex que nos devolverá el número de licencias en uso.
- **table:** *(para el parser webtable)* El encabezado de la sub-subsección de parseado de tablas.
  - **index:** El índice de la tabla a parsear.
- **js:** *(para el parser webtablejs)* El encabezado de la sub-subsección de parámetros javascript.
  - **id:** EL id que buscará la función *find_element_by_id*, habitualmente "mydata"
  - **attr:** El atributo que buscará la función *get_attribute*, habitualmente "innerHTML"
  - **iloc:** La fila de la tabla que queremos seleccionar para procesar, o *None* para tratar la tabla tal cual.
- **label:** *(para los parsers webtable y webtablejs)* El encabezado de la sub-subsección de búsqueda de los encabezados de la tabla.
  - **name:** La etiqueta del nombre del feature.
  - **total:** La etiqueta del total de licencias disponibles.
  - **used:** La etiqueta del número de licencias en uso.
- **label:** *(para el parser rlmutil)*  El encabezado de la sub-subsección de busqueda de etiquetas en la salida del comando rlmutil.
    - **item:** Los items a procesar, normalmente son las eqtiquetas de las versiones que queremos incluir.
    - **count:** La etiqueta que indicará que un item está licenciado.
- **translate:** Encabezado de la sub-subsección de traducción de los nombres de las features. Para algunos productos el nombre es muy descriptivo, pero para otros utilizan un código que no deja nada claro el nombre de la feature. La traducción se realiza sobre el nombre del feature ya parseado.
  - **search:** La expresión regular que buscará un nombre y un sufijo para el código que aparece en el nombre del feature, por si el sufijo expresa la versión del producto.
  - **at_stage:** Dependiendo del parser y del tipo de licencia puede que la traducción haya que realizarla en diferentes pasos de la creación del objeto feature. El valor será un ordinal. Si el valor es *1* la traducción se hará en la creación del objeto feature. El resto de ordinales dependerán de cada uno de los parsers. Se utilizará cuando nos interese discriminar un feature según la versión del mismo por ejemplo.
  - **translations:** El encabezado de la lista de traducciones.  Aparecerán en el fichero yaml como pares *<original: traducción>*
### **Parámetros de la subsección licenses-users** ###
No todos los sistemas de licencias aportan información sobre detalles de los usuarios que están usando cada una de las licencias. Tampoco la información que aportan es igual en todos, por lo que es bastante complicado estandarizar esta parte del parsing.
- **monitor *(True/False)*:** Si se debe procesar el parseo de información de usuarios.
- **url:** *(para los parsers webtable y webtablejs)* Totalmente equivalente a la de la sección features pero correspondiente a la url que nos devuelve los usuarios.
  - **prefix**
  - **suffix**
  - **index** 
- **table:** *(para los parsers webtable y webtablejs)* El encabezado de la sub-subsección de como parsear la tabla de los usuarios.
  - **skip_header:** El índice de la fila que contiene los encabezados si existe, o *null* si no existe.
  - **method:** *(search/index)* El método para localizar los usuarios. Si hay una única tabla que contiene los usuarios de todas las features usaremos el método *search* para que los agrupe por features. Si hay varias tablas, usaremos el método *index*
  - **index:** En el caso del método *index*, el índice de la tabla donde están los usuarios.
- **label:**  *(para los parsers webtable y webtablejs)* El encabezado de la sub-subsección con las etiquetas para extraer información de cada usuario concreto.
  - **featurename:** *(aplicable solo al método search)* La etiqueta de la columna que alberga el nombre de la feature que usa un determinado usuario o *null* si no aplica (en el método *index* por ejemplo).
  - **username:** La etiqueta de la columna que alberga el nombre del usuario.
  - **hostname:** La etiqueta de la columna que alberga el nombre del host.
  - **date:** La etiqueta de la columna que alberga la fecha en que comenzó a usar la licencia.
### **Parámetros específicos del parser rawsocket** ###
- **timeout:** El timeout tras el que si no puede abrir el socket considerará que el servidor de licencias no está activo y no añadirá ninguna feature.
- **recv_bytes:** El número de bytes que intentará leer para comprobar que el socket aparte de poder abrirse devuelve información.
- **connect_only:** En el caso de que simplemente queramos comprobar que hay conexión con el servidor y el puerto sin intentar leer nada más.