Instrucciones de Prueba, instalación y tuneado
==============================================
El siguiente documento explica de forma breve las instrucciones para poder probar la aplicación desde el propio equipo del desarrollador, para instalar los contenedores tanto de forma manual como automática mediante CI/CD, para configurar los paneles de grafana y para usar un servicio de prometheus externo al docker compose si es que se dispone de él.

Las secciones  de este documento son:
1. Pruebas de la aplicación.
2.  Instalación manual.
3.  Instalación automática CI/CD
4.  Configuración del panel de grafana
5.  Configuración de un servidor prometheus externo
6.  Instalación del servidor de selenium

1\. Pruebas de la aplicación
----------------------------
Es posible, y deseable, probar la aplicación antes de proceder a la instalación. Para realizar las pruebas solo es necesario ejecutar el código python:

`python licenses_exporter.py`

La aplicación generará una página web accesible en http://localhost:8000 si es ese el numero de port del fichero de configuración config.yml, o cualquier otro si se cambia. Ve el fichero CONFIGURE.md para más información.

La página web generada contendrá líneas similares a estas:

`
license_feature_used{app="NVIDIAGRID",name="Quadro-Virtual-DWS"} 19.0
license_feature_used{app="ROBOTSTUDIO",name="RobotStudio, 7.x"} 6.0
license_feature_issued{app="MATLAB R2018b",name="MATLAB"} 100.0
license_feature_issued{app="MATLAB R2018b",name="SIMULINK"} 30.0
license_feature_used_users{app="SOLID EDGE",device="DESKTOP-77RPBAR0.0",host="DESKTOP-77RPBAR",name="solidedgeacademicu",user="USER"} 1.0
license_feature_used_users{app="AUTODESK",device="VDI3D-19",host="VDI3D-19",name="Autocad Mechanical 2022",user="z92beblv"} 1.0
license_feature_used_users{app="SPSS",device="None",host="DESKTOP-5QR52M7",name="SPSS Version 25 ",user="JesusAlberto"} 1.0
license_server_status{app="GRAPHER",fqdn="ucolic01.ctx.uco.es",master="true",port="port",version="version"} 1.0
license_server_status{app="PALISADE",fqdn="28000@ucolic02.ctx.uco.es",master="true",port="port",version="version"} 1.0
`

La salida dependerá de número de apps monitorizadas definidas en el fichero de configuración.

De forma paralela la aplicación generará una salida más o menos extensa controlada por las siguientes variables que están al principio del código:

- **SUMMARY**: Presenta solamente una línea por acada aplicación y ciclo con un resumen de los valores parseados.
- **VERBOSE**: Presenta información extendida para cada aplicación y ciclo.
- **DEBUG**: Presenta información de depuración. Además activa la opción verbose.
- **TRACE**: Presenta información de traza de la aplicación, para seguir el flujo del programa en caso de depuración.
- **WRITEHTML**: En el caso de los parsers web, muestra la salida del html capturado del servidor de licencias, útil para la  depuración.

Para las pruebas en local es necesario tener instaladas algunas librerías de python en el equipo donde se realizan las pruebas, estas librerías son las especificadas en el fichero requirements.txt y pueden instalarse con  `pip install`. Cuando se ejecute en un docker no es necesario tenerlas previamente pues el fichero Dockerfile se encargará de instalarlas.

2\. Instalación manual
----------------------
Licenses exporter está compuesto de 3 dockers:
- Docker para prometheus
- Docker para Grafana
- Docker para la aplicación en sí (licenses_exporter.py)

Los tres se generan a partir de un docker-compose (docker-compose.yml) mediante el comando  `docker-compose build` y se ejecutan mediante `docker-compose up` o bien `docker-compose up -d` si se quiere ejecutar como demonio.

En el fichero docker-compose.yml se hace referencia al registro de gitlab de la UCO, en la siguiente línea:

`image: registry.gitlab.uco.es/tonin/licensesexporter`

Se debe adaptar al registry de donde se ejecute, si no se dispone de ninguno propio se puede usar cualquiera público como el de github (https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) u otros.

Una vez levantado el docker compose, el sistema es autocontenido y ofrece todas las funcionalidades (parseo/scrapeo, alimentación de la BBDD y graficación).

En el fichero docker-compose.yml se especifica el mapeo de puertos internos/externos. Por ejemplo, en el docker-compose.yml por defecto de mapea el puerto interno 8000 al externo 9318, luego para acceder a la página web de licenses exporter ejecutándose dentro del docker se usará la URL http://somehost.somedomain:9318, en el caso de grafana se mapea el puerto por defecto 3000 interno al docker al externo 3001, etc.

Estudie el fichero de docker-compose.yml y la documentación de docker para más información y posibilidades, como mapear fuera de los contenedores determinados ficheros como el de configuración de licenses exporter, configuración de grafana, etc. por si quiere tener persistencia de estos ficheros.

3\. Instalación automática CI/CD
--------------------------------
Licenses exporter se suministra con una configuración de ejemplo para CI/CD usando gitlab. En caso de querer usar esta posibilidad en su entorno de gitlab o contra otros entornos CI/CD como el de github, deberá tunear la configuración.

La información de CI/CD está en el fichero .gitlab-ci.yml. Consta de dos stages, build para construir el docker compose y deploy para desplegarlo en producción.

En gitlab es necesario haber instalado un runner (https://gitlab.uco.es/help/ci/runners/README) que es quien se encargará de ejecutar todos los comandos para CI/CD. Puede usarse un runner específico o uno compartido.

Si se usa gitlab, en settings-CI/CD podrá especificar el runner y debará definir en la sección "Variables" las siguientes:
- **CI_DEPLOY_HOME**: Es el directorio del servidor donde se vayan a instalar/ejecutar los dockers.
- **CI_DEPLOY_SERVER**: El FQDN o IP del servidor donde se vayan a ejecutar los dockers.
- **CI_DEPLOY_USER**: El usuario que se usará en el servidor donde se vayan a ejecutar los dockers,
- **ID_RSA**: La clave rsa para que gitlab pueda conectarse al servidor donde se ejecutarán los dockers.

Para el stage de build se usará un docker DIND (https://github.com/jpetazzo/dind) que instalará el propio entorno de CI/CD, y para el deploy usará un docker de alpine, por lo que no hay que hacer nada especial en ambos casos.

El stage build construye los dockers y los sube al repositorio, en este caso el propio del gitlab que se esté usando. Para trabajar con otros entornos CI/CD revise la documentación específica. 

El stage build es invocado automáticamente cuando desde el equipo de desarrollo tras un commit se hace un `git push`. Desde gitbal en la sección CI/CD-Pipelines se verá el trabajo en curso y se podrán monitorizar posibles errores de creación de los dockers para resolverlos.

Tras terminar con el stage build, se genera un nuevo trabajo de deploy, que está configurado  para que sea manual (puede cambiarse a automático alterando la claúsula when: de `.gitlab-ci.yml`). En la consola de gitlab se puede ejecutar este trabajo manual y monitorizar el despliegue.

Revise el fichero .gitlab-ci.yml para ver las operaciones que hace el stage deploy. Verá que es posible desplegarlo en un solo servidor o en varios por si quiere usar docker swarm para tener alta disponibilidad.

Al final del proceso de despliegue el propio script matará el docker compose anterior y lanzará el nuevo. Por todo ello, el ciclo de ejecución de licenses exporter tras cambios en el código o en la configuración será el siguiente:
- Modificar el código o fichero de configuración.
- Hacer `git add`de el fichero o ficheros modificados.
- Hacer `git commit`de los cambios.
- Hacer `git push`para subir los cambios al repositorio de gitlab.
- Desde la consola de gitlab, monitorizar que el stage build termina correctamente.
- Desde la consola de gitlab, ejecutar el trabajo de deploy manual.
- Al terminar lo anterior ya estará la nueva versión en ejecución.

4\. Configuración de los paneles de grafana
-------------------------------------------
La aplicación se suministra con una configuración por defecto para grafana con un panel que incluye los ejemplos de apps del fichero de configuración de ejemplo. Evidentemente esta configuración variará para cada caso, aunque en futuras versiones la configuración se generará automáticamente en función del fichero config.yml

De momento es muy sencillo adaptar el panel a la configuración concreta. Basta con borrar todos los elementos del panel que no se usen y editar los que se modifiquen.

Tanto para los elementos de tipo stat que muestran el estado del servidor de licencias, como para los gráficos de tipo graph que muestran el uso de las mismas, solo es necesario configurar el `app` del Metrics Browser con el valor que se le haya dado a la entrada `name` para esa app en el fichero config.yml.

Aparte de eso evidentemente se le cambiará el Title del elemento del panel y cualquier otra configuración estética que se quiera.

Si se configura un servidor de grafana y prometheus externos al que va en el propio docker compose, hay que configurar en grafana en Configuration-DataSources un data source de tipo prometheus con la URL y puerto de nuestro servidor externo, dejando todos los demás parámetros por defecto.

5\. Configuración de un servidor prometheus externo
---------------------------------------------------
Si su organización dispone de un servidor prometheus externo para centralizar todas las BBDD de métricas de series temporales, puede escrapear desde él los datos que genera licenses exporter.

El fichero prometheus.yml es la configuración del prometheus interno del docker compose, y de él puede sacar la información de escrapeo para configurar su prometheus, en el prometheus.yml del proyecto tenemos:

```yaml
- job_name: 'licenses'
    scrape_interval: 1m
    static_configs:
      - targets: ['licensesexporter:8000']
        labels:
          group: 'Licencias'
```
Al ser el target local se puede poner cualquier cosa que identifique la métrica; si el target fuera remoto se pondría una configuración de este estilo:

```yaml
  - job_name: "licenses"
    static_configs:
      - targets:
        - mihost.midominio.es:9318
```
Poniendo el FQDN donde se esté ejecutando licenses exporter y el puerto **externo** que se configurara en el docker-compose.

El resto de información de configuración de prometheus, como puede ser el tiempo de escrapeo (que se recomienda coincida con el tiempo de ciclo del config.yml), el tiempo de retención de los datos, etc. se configura como  se quiera siguiendo la documentación de prometheus (https://prometheus.io/docs/prometheus/latest/configuration/configuration/)

6\. Instalación del servidor de selenium
----------------------------------------

Selenium se utiliza para renderizar las páginas webs de los servidores de licencias que usan javascript. La forma más sencilla de instalar el servicio de selenium es usar el docker de https://github.com/SeleniumHQ/docker-selenium.

En README de este proyecto están las instrucciones de instalación del hub de selenium. Aparte hace falta un nodo con chrome, que es otro docker cuyas instrucciones de instalación están aquí: https://hub.docker.com/r/selenium/node-chrome

En el fichero de configuración se configura la URL y puertos de acceso al servidor de selenium en el caso de que el webdriver se defina como remoto. Si se usa el webdriver local, para realizar pruebas del punto 1 sin haber montado nada de dockers aún por ejemplo, lo que se arrancará será el navegador local de chrome.
