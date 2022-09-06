# Reimplementation of speech decoding paper by MetaAI

**Please let me know if you think I shouldn't make this repo public because MetaAI hasn't provided the official implementation.**

Paper: https://arxiv.org/pdf/2208.12266.pdf

<div align="center"><img src="overview_meta2022.png" width=300></div>

## Status

Under development. CLIP loss seems not working properly.

## Dataset

4 datasets were used in the paper (2 EEG and 2 MEG). Because speech audio was not available for Broderick2019, I'm only using Brennan2019. I haven't checked for two MEG datasets.

**Brennan et al., 2019**

- Paper https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0207741

- Dataset https://deepblue.lib.umich.edu/data/concern/data_sets/bg257f92t

You will need `S01.mat` to `S49.mat` placed under `data/Brennan2018/raw/` to run the code.

I provide merged version of the audio files [here](https://drive.google.com/file/d/1qXyDFHhIKw7e-llEklLh02D6DuSTTqFg/view?usp=sharing).

## wav2vec 2.0

`wav2vec2-large-xlsr-53` model was used for speech embedding. You will need to download `xlsr_53_56k.pt` from [here](https://github.com/facebookresearch/fairseq/tree/main/examples/wav2vec) and place it under `weights/`.