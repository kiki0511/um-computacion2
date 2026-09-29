#!/usr/bin/env python3
"""
Ejercicios adicionales - Clase 20.

Modos:
  chat      → chat.py de la clase 17 reescrito con asyncio streams
  comandos  → comandos.py de la clase 16 (socketserver) pasado a asyncio
  proxy     → proxy TCP asíncrono: dos tareas por conexión, cancela una
              cuando la otra termina
  demo      → prueba automática de los tres

Uso:
  python3 ej_extra_adicionales.py chat [puerto]
  python3 ej_extra_adicionales.py comandos [puerto]
  python3 ej_extra_adicionales.py proxy <puerto_local> <host_destino> <puerto_destino>
  python3 ej_extra_adicionales.py demo
"""
import asyncio
import sys
import time


# ─────────────────────────────────────────────
# Chat
# ─────────────────────────────────────────────

class Chat:
    def __init__(self):
        self.escritores = {}              # writer -> apodo

    async def difundir(self, texto, excepto=None):
        for w in list(self.escritores):
            if w is excepto:
                continue
            try:
                w.write(texto.encode())
                await w.drain()           # backpressure por cliente
            except ConnectionError:
                self.escritores.pop(w, None)

    async def manejar(self, reader, writer):
        h, p = writer.get_extra_info('peername')[:2]
        self.escritores[writer] = f'{h}:{p}'
        writer.write(b'Bienvenido. /nick <nombre>, /lista\n')
        await self.difundir(f'* se conectó {self.escritores[writer]}\n', excepto=writer)
        try:
            # readline() ya resuelve el framing que en la clase 17 hubo que hacer a mano
            while linea := await reader.readline():
                texto = linea.decode(errors='replace').strip()
                if not texto:
                    continue
                apodo = self.escritores[writer]
                if texto.startswith('/nick '):
                    self.escritores[writer] = texto[6:].strip() or apodo
                    await self.difundir(f'* {apodo} ahora es {self.escritores[writer]}\n')
                elif texto == '/lista':
                    writer.write(f'* {", ".join(self.escritores.values())}\n'.encode())
                    await writer.drain()
                else:
                    await self.difundir(f'<{apodo}> {texto}\n', excepto=writer)
        except ConnectionError:
            pass
        finally:
            apodo = self.escritores.pop(writer, '?')
            writer.close()
            await self.difundir(f'* se fue {apodo}\n')


# ─────────────────────────────────────────────
# Servidor de comandos
# ─────────────────────────────────────────────

class Comandos:
    """Mismo estado que en la clase 16, SIN Lock: entre dos await nadie
    más corre, y ninguna sección crítica tiene un await adentro."""

    def __init__(self):
        self.conexiones = 0
        self.activos = set()

    async def manejar(self, reader, writer):
        direccion = writer.get_extra_info('peername')[:2]
        self.conexiones += 1
        self.activos.add(direccion)

        def responder(t):
            writer.write((t + '\n').encode())

        responder('Servidor de comandos async. Escribí AYUDA.')
        try:
            while True:
                try:
                    linea = await asyncio.wait_for(reader.readline(), 30)   # timeout inactividad
                except asyncio.TimeoutError:
                    responder('Desconectado por inactividad')
                    break
                if not linea:
                    break
                partes = linea.decode(errors='replace').strip().split(maxsplit=1)
                if not partes:
                    continue
                cmd, resto = partes[0].upper(), (partes[1] if len(partes) > 1 else '')
                if cmd == 'TIME':
                    responder(time.strftime('%Y-%m-%d %H:%M:%S'))
                elif cmd == 'ECHO':
                    responder(resto)
                elif cmd == 'QUIEN':
                    responder(f'{len(self.activos)} conectados: '
                              + ', '.join(f'{h}:{p}' for h, p in sorted(self.activos)))
                elif cmd == 'CONTADOR':
                    responder(f'Conexiones totales desde el arranque: {self.conexiones}')
                elif cmd == 'AYUDA':
                    responder('TIME | ECHO <texto> | QUIEN | CONTADOR | QUIT')
                elif cmd == 'QUIT':
                    responder('Chau')
                    break
                else:
                    responder(f'Comando desconocido: {cmd}')
                await writer.drain()
        finally:
            self.activos.discard(direccion)
            writer.close()


# ─────────────────────────────────────────────
# Proxy
# ─────────────────────────────────────────────

async def bombear(reader, writer):
    while datos := await reader.read(65536):
        writer.write(datos)
        await writer.drain()
    writer.close()


def crear_proxy(host_dest, puerto_dest):
    async def manejar(r_cli, w_cli):
        try:
            r_dst, w_dst = await asyncio.open_connection(host_dest, puerto_dest)
        except OSError:
            w_cli.close()
            return
        ida = asyncio.create_task(bombear(r_cli, w_dst))
        vuelta = asyncio.create_task(bombear(r_dst, w_cli))
        # cuando un sentido termina (alguien cerró), cancelar el otro
        _, pendientes = await asyncio.wait({ida, vuelta}, return_when=asyncio.FIRST_COMPLETED)
        for t in pendientes:
            t.cancel()
        w_cli.close()
        w_dst.close()
    return manejar


# ─────────────────────────────────────────────
# Demo
# ─────────────────────────────────────────────

async def demo():
    # chat
    chat = Chat()
    srv = await asyncio.start_server(chat.manejar, '127.0.0.1', 0)
    p = srv.sockets[0].getsockname()[1]
    ra, wa = await asyncio.open_connection('127.0.0.1', p)
    rb, wb = await asyncio.open_connection('127.0.0.1', p)
    await ra.readline(); await rb.readline(); await ra.readline()   # bienvenidas y aviso
    wa.write(b'/nick ana\nhola a todos\n')
    await wa.drain()
    print('chat     → B recibe:', (await rb.readline()).decode().strip(),
          '|', (await rb.readline()).decode().strip())
    wa.close(); wb.close()
    srv.close()

    # comandos
    cmds = Comandos()
    srv = await asyncio.start_server(cmds.manejar, '127.0.0.1', 0)
    p = srv.sockets[0].getsockname()[1]
    r, w = await asyncio.open_connection('127.0.0.1', p)
    await r.readline()
    for c in ('ECHO hola', 'CONTADOR', 'QUIEN'):
        w.write((c + '\n').encode())
        print(f'comandos → {c:<9}: {(await r.readline()).decode().strip()}')
    w.close()
    srv.close()

    # proxy delante de un eco
    async def eco(reader, writer):
        while d := await reader.read(100):
            writer.write(d.upper())
            await writer.drain()
        writer.close()
    srv_eco = await asyncio.start_server(eco, '127.0.0.1', 0)
    p_eco = srv_eco.sockets[0].getsockname()[1]
    srv_px = await asyncio.start_server(crear_proxy('127.0.0.1', p_eco), '127.0.0.1', 0)
    p_px = srv_px.sockets[0].getsockname()[1]
    r, w = await asyncio.open_connection('127.0.0.1', p_px)
    w.write(b'pasando por el proxy')
    await w.drain()
    print('proxy    →', (await r.read(100)).decode())
    w.close()
    srv_eco.close(); srv_px.close()


async def servir(manejar, puerto):
    srv = await asyncio.start_server(manejar, '0.0.0.0', puerto)
    print(f'Escuchando en {puerto}. Ctrl+C para cortar.')
    async with srv:
        await srv.serve_forever()


if __name__ == '__main__':
    args = sys.argv[1:]
    modo = args[0] if args else ''
    try:
        if modo == 'demo':
            asyncio.run(demo())
        elif modo == 'chat':
            asyncio.run(servir(Chat().manejar, int(args[1]) if len(args) > 1 else 8080))
        elif modo == 'comandos':
            asyncio.run(servir(Comandos().manejar, int(args[1]) if len(args) > 1 else 8080))
        elif modo == 'proxy' and len(args) == 4:
            asyncio.run(servir(crear_proxy(args[2], int(args[3])), int(args[1])))
        else:
            print(__doc__)
            sys.exit(1)
    except KeyboardInterrupt:
        print('\nChau.')
