"""
Verifica uma vez se a pasta 'dados' mudou e, se mudou, publica.

Com a opção --sempre, gera e publica em toda passada, sem comparar nada — é o
mesmo efeito de apertar o publicar.bat. Como o git só registra o que mudou de
verdade, passadas sem novidade não geram commit.

Foi feito para o Agendador de Tarefas do Windows chamar de dois em dois minutos,
sem janela aberta e sem ninguém apertar nada. Quem prefere acompanhar na tela
continua podendo usar o sincronizar.bat, que faz a mesma coisa de forma visível.

Para ligar o agendamento: dois cliques em agendar.bat (uma vez só).
Para desligar: dois cliques em desagendar.bat.
O que aconteceu em cada passada fica registrado em publicacao.log.
"""

import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
ENTRADA = BASE / "dados"
ESTADO = BASE / ".estado_publicacao.json"
LOG = BASE / "publicacao.log"

INICIOS = ["mata121", "mata110", "PROD_EM_PP", "SALDO"]
PLANILHAS = (".xlsx", ".xlsm", ".xls")
ESPERA_COPIA = 8          # segundos para conferir se o arquivo parou de mudar


def log(msg):
    linha = f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] {msg}"
    print(linha, flush=True)
    try:
        antigas = LOG.read_text(encoding="utf-8").splitlines() if LOG.exists() else []
        antigas.append(linha)
        LOG.write_text("\n".join(antigas[-300:]) + "\n", encoding="utf-8")
    except OSError:
        pass


def impressao_digital():
    if not ENTRADA.exists():
        return []
    marcas = []
    for arquivo in sorted(ENTRADA.iterdir()):
        if (arquivo.is_file()
                and arquivo.suffix.lower() in PLANILHAS
                and not arquivo.name.startswith("~$")
                and any(arquivo.name.lower().startswith(i.lower()) for i in INICIOS)):
            info = arquivo.stat()
            marcas.append([arquivo.name, info.st_size, round(info.st_mtime)])
    return marcas


def rodar(comando):
    return subprocess.run(comando, cwd=BASE, shell=True, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


GERADOS = ["dados.js", "historico.js"]


def conteudo_util():
    """Impressão digital do que foi gerado, ignorando data e hora. Serve para saber
    se a base realmente mudou: sem isso, publicando de 5 em 5 minutos, o carimbo de
    hora sozinho geraria um commit a cada passada."""
    partes = []
    for nome in GERADOS:
        arq = BASE / nome
        if arq.exists():
            texto = arq.read_text(encoding="utf-8")
            texto = re.sub(r'"(hora|gerado)":"[^"]*",?', "", texto)
            partes.append(texto)
    return hashlib.sha1("".join(partes).encode("utf-8")).hexdigest()


def publicar(sempre=False):
    saida = rodar(f'"{sys.executable}" gerar_dados.py')
    if saida.returncode != 0:
        ultima = (saida.stderr or saida.stdout or "").strip().splitlines()
        log("Falhou ao gerar a base. " + (ultima[-1] if ultima else ""))
        return False

    marca = conteudo_util()
    if sempre and marca == estado().get("conteudo"):
        rodar("git checkout -- " + " ".join(GERADOS))     # desfaz só a troca de horário
        return True

    rodar("git add -A")
    if rodar("git diff --cached --quiet").returncode == 0:
        if not sempre:
            log("Arquivos novos, mas a base gerada é igual à publicada. Nada a enviar.")
        guardar_estado(conteudo=marca)
        return True

    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    if rodar(f'git commit -m "atualiza base {agora}"').returncode != 0:
        log("O commit falhou.")
        return False
    if rodar("git push").returncode != 0:
        log("O envio falhou. Tento de novo na próxima passada.")
        return False

    guardar_estado(conteudo=marca)
    log("Publicado. Os aparelhos com o monitor aberto trocam de base em poucos minutos.")
    return True


def estado():
    if ESTADO.exists():
        try:
            guardado = json.loads(ESTADO.read_text(encoding="utf-8"))
            return guardado if isinstance(guardado, dict) else {"marcas": guardado}
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def guardar_estado(**campos):
    atual = estado()
    atual.update(campos)
    try:
        ESTADO.write_text(json.dumps(atual), encoding="utf-8")
    except OSError:
        pass


def main():
    sempre = "--sempre" in sys.argv

    atual = impressao_digital()
    if not atual:
        return

    if sempre:                                  # faz o mesmo que o publicar.bat, sem perguntar
        if publicar(sempre=True):
            guardar_estado(marcas=atual)
        return

    anterior = estado().get("marcas")
    if anterior is None:                        # primeira vez: só registra o que existe hoje
        guardar_estado(marcas=atual)
        log("Primeira verificação. Base atual registrada; a próxima troca de arquivo publica.")
        return

    if atual == anterior:
        return                                  # nada mudou, sai em silêncio

    log("Arquivo novo na pasta dados. Conferindo se a cópia terminou...")
    time.sleep(ESPERA_COPIA)
    if impressao_digital() != atual:
        log("Ainda estava copiando. Deixo para a próxima passada.")
        return

    if publicar():
        guardar_estado(marcas=atual)


if __name__ == "__main__":
    main()
