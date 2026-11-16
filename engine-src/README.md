# Engine b18 do Aurora

O aplicativo distribui uma compilação local do backend WebGPU/CPU do projeto saigo-online/katago-webgpu, derivado de lightvector/KataGo. Consulte `provenance.json` para a revisão exata e os hashes. As licenças estão em `static/vendor/katago/licenses/`.

Alterações em `aurora.patch`: configuração explícita das regras e pedras iniciais; rejeição de lances ilegais; invalidação da árvore ao mudar regras/komi/setup; layout NHWC no backend Eigen; ativações WGSL Mish/SiLU com fórmulas equivalentes que evitam overflow na GPU Apple. A API de entrada do Emscripten preserva mainScriptUrlOrBlob para os pthreads.

Para recompilar, clone a revisão indicada, aplique `git apply aurora.patch` na raiz do clone, instale/ative o SDK Emscripten 6.0.13 e extraia Eigen 3.4.0. Use Python 3.13:

```
python3.13 engine-src/build.py --katago /caminho/katago-webgpu --sdk /caminho/emsdk --eigen /caminho/eigen-3.4.0 --output static/vendor/katago
```

Fontes sem modificações do Eigen (MPL2 e licenças permissivas): https://gitlab.com/libeigen/eigen/-/tree/3.4.0. SDK: https://github.com/emscripten-core/emsdk. Backend WebGPU: https://github.com/saigo-online/katago-webgpu. Rede oficial: https://katagotraining.org/networks/. O arquivo da rede é distribuído junto ao pacote para execução local sem download externo em tempo de uso.

O clone do GitHub não inclui o arquivo da rede b18. Veja as instruções no README principal para obtê-lo.
