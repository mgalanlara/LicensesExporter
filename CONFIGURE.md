Configuración de licenses exporter
==================================

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