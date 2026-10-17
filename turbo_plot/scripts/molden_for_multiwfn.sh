#!/bin/bash
# molden do TURBOMOLE -> molden_new.molden esferico com TODOS os MOs (virtuais incluidos).
# molden2aim descarta Occup=0; por isso marca tudo como ocupado, converte e restaura Occup=0 acima do HOMO.
set -e; NOCC=${1:-167}; SRC=${2:-../ni.molden}
python3 - "$SRC" <<'P'
import re,sys
s=re.sub(r"Occup=\s*[-\d.Ee+]+","Occup= 2.000000",open(sys.argv[1]).read())
open("molden.input","w").write("[Program] turbomole\n"+s)
P
echo 'carsph=1' > m2a.ini; ulimit -s unlimited
printf "No\n" | ~/local_bin/molden2aim.exe -i molden.input > m2a.log 2>&1 || true   # sai com codigo != 0 no prompt final
python3 - "$NOCC" <<'P'
import re,sys
n=int(sys.argv[1]); h,mo=open("molden_new.molden").read().split("[MO]"); c=[0]
def f(m):
    c[0]+=1; return "Occup= 2.00000000" if c[0]<=n else "Occup= 0.00000000"
open("molden_new.molden","w").write(h+"[MO]"+re.sub(r"Occup=\s*[-\d.Ee+]+",f,mo))
P
rm -f *123456789.tmp molden.input molden.wfn
