from pathlib import Path
import subprocess,os
import argparse,sys
parser=argparse.ArgumentParser();parser.add_argument('--katago',required=True);parser.add_argument('--sdk',required=True);parser.add_argument('--eigen',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
root=(Path(args.katago)/'cpp').resolve();sdk=Path(args.sdk).resolve();eigen=Path(args.eigen).resolve()
emcc=[sys.executable,str(sdk/'upstream/emscripten/emcc.py')]
env=os.environ.copy();env['EM_CONFIG']=str(sdk/'.emscripten');env['PATH']=str(sdk/'python/3.13.3_64bit/bin')+':'+str(sdk/'node/24.19.0_64bit/bin')+':'+env['PATH']
flags=['-O2','-fexceptions','-DNO_GIT_REVISION','-DHALF_ENABLE_CPP11_CFENV=0','-I','external','-isystem','external/filesystem-1.5.8/include','--use-port=emdawnwebgpu','-sUSE_ZLIB=1','-pthread','-DKGE_THREADS']
sources=[]
for manifest in ('sources.txt','sources-search.txt'):
 sources.extend(line.strip() for line in (root/'kataeval'/manifest).read_text().splitlines() if line.strip() and not line.startswith('#'))
obj=root/'build-aurora/obj';obj.mkdir(parents=True,exist_ok=True);objects=[]
for i,f in enumerate(sources):
 out=obj/(f.replace('/','_').replace('.','_')+'.o');objects.append(str(out))
 if out.exists() and out.stat().st_mtime>=(root/f).stat().st_mtime:continue
 print(f'[{i+1}/{len(sources)}] {f}',flush=True)
 extra=['-DUSE_EIGEN_BACKEND','-isystem',str(eigen)] if f=='kataeval/backend_cpu.cpp' else []
 subprocess.run(emcc+[str(root/f),'-c','-std='+('c++20' if f=='kataeval/backend_gpu.cpp' else 'c++17')]+flags+extra+['-o',str(out)],cwd=root,env=env,check=True)
export='_kgeLoad,_kgeSetPositionConfig,_kgeError,_kgeBoardSize,_kgeModelVersion,_kgeBackendIsGpu,_kgeSetForceCpu,_kgeEvalSeqKata,_kgeSearchKata,_kgeStopSearch,_malloc,_free'
out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
subprocess.run(emcc+objects+['-sDEFAULT_TO_CXX','--use-port=emdawnwebgpu','-sUSE_ZLIB=1','-pthread','-fexceptions','-sASYNCIFY','-sALLOW_MEMORY_GROWTH=1','-sFORCE_FILESYSTEM=1','-sSTACK_SIZE=8MB','-sPTHREAD_POOL_SIZE=5','-sINITIAL_MEMORY=512MB','-sINCOMING_MODULE_JS_API=print,printErr,locateFile,mainScriptUrlOrBlob,onAbort,onRuntimeInitialized,wasmBinary','-sMODULARIZE=1','-sEXPORT_NAME=createAuroraKata','-sEXPORTED_FUNCTIONS='+export,'-sEXPORTED_RUNTIME_METHODS=ccall,FS,HEAPF32,HEAP32,UTF8ToString','-O2','-o',str(out/'katago.js')],cwd=root,env=env,check=True)
print('WASM built',flush=True)
