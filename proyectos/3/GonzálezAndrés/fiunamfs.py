from mmap import mmap
import re

MSGERR_NO_MONTADO = 'Error: No se ha montado el sistema de archivos'
MSGERR_ARCH_NO_ENC = 'Error: No se encuentra el archivo de origen'
MSGADV_FS_YA_MONT = 'Advertencia: El sistema de archivos ya está montado'
MSGERR_FN_INVALIDO = 'Error: el nombre de destino debe incluir de 1 a 16 caracteres (imprimibles US-ASCII)'

PATRON_FN = re.compile(r'[\x21-\x7F][\x20-\x7F]{,16}') # Patrón para verificar si los archivos tienen caracteres válidos

class FIUNAMFS(object):
    def __init__(self, ruta_img):
        self.ruta_img = ruta_img
        self.__listaEntDir = []
        self.montado = False

    def montar(self):
        if self.montado:   
            print(MSGADV_FS_YA_MONT)
            return True 
                    
        try:
            self.__f = open(self.ruta_img, 'r+b')
        except OSError:
            print('No se puede abrir %s' % self.ruta_img)
        except IOError as e:
            print('IOError %s' % e)
        else:
            self.__mmfs = mmap(self.__f.fileno(), 0)
            nombrefs = self.__mmfs[0:8].decode('ascii')
            # print(nombrefs)
            if nombrefs == 'FiUnamFS':
                self.montado = True

                self.nombre = nombrefs
                # print('Nombre del sistema de archivos: %s' % self.nombre)

                self.version = self.__mmfs[10:13].decode('ascii').strip()
                # print('Versión: %s' % self.version)
                
                self.etiqueta = self.__mmfs[20:35].decode('ascii').strip()
                # print('Etiqueta del volumen: %s' % self.etiqueta)
                
                self.tam_cluster = int(self.__mmfs[40:45].decode('ascii').strip())
                # print('Tamaño del cluster: %i bytes' % self.tam_cluster)

                self.tam_dir = int(self.__mmfs[47:49].decode('ascii').strip())
                # print('Tamaño del directorio: %i clusters' % self.tam_dir)

                self.tam_unidad = int(self.__mmfs[52:60].decode('ascii').strip())
                # print('Tamaño de la unidad: %i clusters' % self.tam_unidad)

                self.tam_entradadir = 64

                self.scandir()

                print('Sistema de archivos montado')
                return True
            else:
                print('No se reconoce el sistema de archivos')
                self.__mmfs.close()
                self.montado = False
                return False

    def desmontar(self):
        if self.montado:
            self.__mmfs.close()
            self.__f.close()
            self.montado = False
            print('Sistema de archivos desmontado')
        else:
            print(MSGERR_NO_MONTADO)

    def listdir(self):
        ldir = []
        if self.montado:
            for entradaDir in self.__listaEntDir:
                ldir.append(entradaDir.nombre)
        else: 
            print(MSGERR_NO_MONTADO)
        return ldir
    
    def scandir(self):
        self.__listaEntDir = []
        if self.montado:
            inicio = self.tam_cluster
            fin = self.tam_cluster*self.tam_dir+self.tam_cluster
            paso = self.tam_entradadir
            for i in range(inicio,fin,paso):
                entdir = self.__mmfs[i:i+paso]
                nombre = entdir[0:15].decode('ascii').strip()
                # if nombre == 'README.org':                    
                #     print(len(('\0'*3+'24527').encode('ascii')), ('\0'*8+'24527').encode('ascii'))
                #     print(len(self.__mmfs[i+16:i+24]), self.__mmfs[i+16:i+24])
                #     self.__mmfs[i+16:i+24] = ('00029718').encode('ascii')
                #     self.__mmfs.flush()
                if nombre != 'Xx.xXx.xXx.xXx.':
                    tam_archivo = int(entdir[16:24].decode('ascii').strip())
                    cluster_inicial = int(entdir[25:30].decode('ascii').strip())
                    f_creacion = entdir[31:45].decode('ascii')
                    f_modif = entdir[46:60].decode('ascii')
                    nuevaEntrada = EntradaDir(nombre, tam_archivo, cluster_inicial, f_creacion, f_modif)
                    self.__listaEntDir.append(nuevaEntrada)
        else:
            print(MSGERR_NO_MONTADO)
        return self.__listaEntDir

    def descargar(self, origen = '', destino = ''):
        """Copiar un archivo de FIUNAMFS a nuestro sistema de archivos
        Atributos:
            origen -- nombre del archivo a copiar
            destino -- ruta y nombre del archivo de destino
        """
        if not self.montado:
            print(MSGERR_NO_MONTADO)
            return False

        resultado = list(filter( lambda entdir: entdir.nombre == origen, self.__listaEntDir)) # Buscamos el elemento que coincida
        if not resultado:
            print(MSGERR_ARCH_NO_ENC)
            return False
        
        entrDir = resultado.pop() # Obtenemos la entrada del directorio
        dir_inicio = entrDir.cluster_inicial * self.tam_cluster # dirección de inicio
        dir_fin = dir_inicio + entrDir.tam_archivo # dirección de fin
        bytes_archivo = self.__mmfs[dir_inicio:dir_fin] # bytes en bruto
        try:
            destino = origen if not destino else destino # Usar el mismo nombre que el del origen si no le dimos ninguno
            f = open(destino, 'w+b') # Abrimos el archivo en modo w+b
            f.write(bytes_archivo)
            f.close()
            print('Se escribió el archivo %s' % destino)
            return True
        except IOError as ioerr:
            print('IOError: %s' % ioerr)            
    
    def subir(self, origen, destino):
        destino = destino.strip() # Le quitamos los caracteres en blanco al inicio y al final
        if not destino:
            destino = origen
        if not self.montado:
            print(MSGERR_NO_MONTADO)
            return False
        if not re.fullmatch(PATRON_FN, destino): # Checamos si el nombre de destino cumple con el regex
            print(MSGERR_FN_INVALIDO)
            print('Nombre ingresado: %s' % destino)
            return False
        print('Guardando... %s -> %s' % (origen, destino))




class EntradaDir(object):
    def __init__(self, nombre, tam_archivo, cluster_inicial, f_creacion, f_modif):
        self.nombre = nombre
        self.tam_archivo = tam_archivo
        self.cluster_inicial = cluster_inicial
        self.f_creacion = f_creacion
        self.f_modif = f_modif

    def __str__(self):
        return '%i %s %i bytes %s %s' % (self.tam_archivo, 
                                    self.nombre, 
                                    self.cluster_inicial, 
                                    self.f_creacion, 
                                    self.f_modif)

# Error de sistema no montado
# class NMError(Error):
#     def __init__(self, expression, message):
#         self.expression = expression
#         self.message = message