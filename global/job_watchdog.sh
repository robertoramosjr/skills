#!/bin/bash
# job_watchdog.sh — watchdog de TRAVAMENTO, padrão em todo job (regra do usuário, 2026-11-12).
# Motivo: jobs 1931613/1931621 (Ag2CrO4, coaraci) ficaram 55 h e 31 h com o VASP parado
# (mpirun vivo, saida.out sem crescer) até o TIMEOUT de 3 d: ~7 mil núcleo-h perdidos.
#
# Uso (no job.sh, depois do bloco de ambiente):
#   source ~/skills/global/job_watchdog.sh
#   run_watched mpirun -np 48 vasp_std > saida_$j.out 2>&1
#   rc=$?          # 124 = travou e foi morto (marcador STALLED criado no diretório)
#
# Critério: o comando é rodado em grupo de processos próprio; a cada poll olha o mtime mais recente
# entre os arquivos do diretório atual (inclui o stdout redirecionado). Sem mudança por
# WATCHDOG_IDLE_SEC → SIGTERM no grupo, 20 s depois SIGKILL, grava STALLED + linha em WATCHDOG_LOG.
# Variáveis (opcionais):
#   WATCHDOG_IDLE_SEC  limite de inatividade, padrão 2700 (45 min). Subir (ex. 7200) só quando um
#                      passo legítimo escreve menos que isso (SCF de >250 átomos, LOBSTER, aoforce).
#   WATCHDOG_GRACE_SEC carência inicial antes de contar (setup/leitura de WAVECAR), padrão 900.
#   WATCHDOG_POLL_SEC  intervalo, padrão min(60, IDLE/4).
#   WATCHDOG_LOG       arquivo de log (padrão ./watchdog.log).
#   WATCHDOG_DIR       diretório observado (padrão $PWD no momento da chamada).
# Não cobre deadlock em que o programa continua escrevendo; só inatividade de saída.

run_watched() {
  local idle=${WATCHDOG_IDLE_SEC:-2700} grace=${WATCHDOG_GRACE_SEC:-900}
  local poll=${WATCHDOG_POLL_SEC:-$(( idle/4 < 60 ? (idle/4 > 0 ? idle/4 : 1) : 60 ))}
  local dir=${WATCHDOG_DIR:-$PWD} log=${WATCHDOG_LOG:-$PWD/watchdog.log}
  local pid pgid last now t0 rc
  t0=$(date +%s)
  setsid "$@" &
  pid=$!
  while kill -0 "$pid" 2>/dev/null; do
    sleep "$poll"
    kill -0 "$pid" 2>/dev/null || break
    now=$(date +%s)
    (( now - t0 < grace )) && continue
    last=$(find "$dir" -maxdepth 1 -type f ! -name STALLED -printf '%T@\n' 2>/dev/null | sort -n | tail -1)
    last=${last%.*}; last=${last:-$t0}
    if (( now - last > idle )); then
      pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')
      echo "$(date '+%F %T') STALLED: sem escrita em $dir há $(( (now-last)/60 )) min (limite $((idle/60)) min); matando grupo ${pgid:-$pid} de: $*" >> "$log"
      touch "$dir/STALLED"
      kill -TERM -- "-${pgid:-$pid}" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
      sleep 20
      kill -KILL -- "-${pgid:-$pid}" 2>/dev/null || kill -KILL "$pid" 2>/dev/null
      wait "$pid" 2>/dev/null
      return 124
    fi
  done
  wait "$pid"; rc=$?
  return $rc
}
