"""
Vigia da pasta 'dados': publica a base sozinho quando os arquivos do Protheus mudam.

Deixe este programa rodando em uma janela no seu computador. Sempre que você salvar
uma exportação nova em dados/ (substituindo mata121.xlsx, mata110.xlsx ou PROD_EM_PP.xlsx),
ele espera o arquivo terminar de copiar, gera o dados.js, faz o commit e o push.
Os aparelhos com o monitor aberto trocam de base em poucos minutos, sem ninguém mexer.

Para rodar: dois cliques em sincronizar.bat, ou 'python sincronizar.py' no terminal.
Para parar: feche a janela ou aperte Ctrl+C.
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
ENTRADA = BASE / "dados"
INICIOS = ["mata121", "mata110", "PROD_EM_PP", "SALDO"]
PLANILHAS = (".xlsx", ".xlsm", ".xls")

INTERVALO = 10          # de quantos em quantos segundos olha a pasta
ESPERA_ESTAVEL = 2      # leituras iguais seguidas antes de considerar a cópia terminada


def agora():
    return datetime.now().strftime("%H:%M:%S")


def log(msg):
    print(f"[{agora()}] {msg}", flush=True)


def achar(inicio):
    """Todos os arquivos que começam com o nome dado. Tolera 'mata121 (1).xlsx',
    'mata121.xlsx.xlsx' e maiúsculas trocadas. O saldo vem em mais de um arquivo,
    porque as filiais estão em grupos diferentes no Protheus."""
    if not ENTRADA.exists():
        return []
    return sorted(a for a in ENTRADA.iterdir()
                  if a.is_file()
                  and a.name.lower().startswith(inicio.lower())
                  and a.suffix.lower() in PLANILHAS
                  and not a.name.startswith("~$"))


def impressao_digital():
    """Tamanho e data de modificação de cada arquivo vigiado: muda se alguém salvou
    por cima. Qualquer um deles mudando já dispara a publicação."""
    marcas = []
    for inicio in INICIOS:
        for caminho in achar(inicio):
            info = caminho.stat()
            marcas.append((caminho.name, info.st_size, round(info.st_mtime)))
    return tuple(sorted(marcas))


def rodar(comando, silencioso=False):
    resultado = subprocess.run(comando, cwd=BASE, shell=True,
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
    if resultado.stdout and not silencioso:
        for linha in resultado.stdout.strip().splitlines():
            log("   " + linha)
    return resultado


def publicar():
    log("Gerando o dados.js...")
    saida = rodar(f'"{sys.executable}" gerar_dados.py')
    if saida.returncode != 0:
        log("Falhou ao gerar a base. Confira os arquivos da pasta dados.")
        if saida.stderr:
            log("   " + saida.stderr.strip().splitlines()[-1])
        return False

    rodar("git add -A", silencioso=True)
    if rodar("git diff --cached --quiet", silencioso=True).returncode == 0:
        log("A base gerada é igual à publicada. Nada a enviar.")
        return True

    hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
    if rodar(f'git commit -m "atualiza base {hoje}"', silencioso=True).returncode != 0:
        log("O commit falhou.")
        return False

    log("Enviando para o GitHub...")
    if rodar("git push", silencioso=True).returncode != 0:
        log("O envio falhou. Vou tentar de novo na próxima mudança ou quando a rede voltar.")
        return False

    log("Publicado. Os aparelhos com o monitor aberto trocam de base em poucos minutos.")
    return True


def main():
    if not ENTRADA.exists():
        log("Não achei a pasta 'dados' aqui do lado. Rode este programa dentro da pasta do monitor.")
        input("Enter para fechar.")
        return

    print()
    print("  == MONITOR PC E SC ALMOXARIFADO ==")
    print("  Vigiando a pasta abaixo. Salve as exportacoes novas do Protheus la dentro")
    print("  e eu publico sozinho. Deixe esta janela aberta. Ctrl+C para parar.")
    print()
    print("  PASTA VIGIADA:")
    print("  " + str(ENTRADA.resolve()))
    print()

    anterior = impressao_digital()
    if not anterior:
        log("Nao achei nenhuma das planilhas do Protheus nessa pasta.")
        presentes = [a.name for a in sorted(ENTRADA.iterdir())] if ENTRADA.exists() else []
        if presentes:
            log("O que existe la dentro: " + ", ".join(presentes))
        else:
            log("A pasta esta vazia.")
        log("Esperados: mata121, mata110, PROD_EM_PP e os arquivos SALDO.")
        log("Se os seus arquivos estao em outra pasta 'monitor', rode o sincronizar.bat que fica la.")
    else:
        for nome, tamanho, _ in anterior:
            log(f"Encontrado: {nome} ({tamanho//1024} KB)")
        log("Vigiando. Base atual registrada.")

    pendente = None
    iguais = 0

    while True:
        try:
            time.sleep(INTERVALO)
            atual = impressao_digital()

            if atual == anterior:
                continue

            # alguém mexeu nos arquivos: espera parar de mudar antes de publicar
            if atual == pendente:
                iguais += 1
            else:
                pendente = atual
                iguais = 0
                log("Arquivo novo detectado. Esperando a cópia terminar...")

            if iguais >= ESPERA_ESTAVEL:
                if publicar():
                    anterior = atual
                pendente = None
                iguais = 0

        except KeyboardInterrupt:
            print()
            log("Vigia encerrado.")
            return
        except Exception as erro:          # rede caiu, arquivo travado pelo Excel, etc.
            log(f"Contratempo: {erro}. Continuo vigiando.")
            time.sleep(INTERVALO)


if __name__ == "__main__":
    main()
