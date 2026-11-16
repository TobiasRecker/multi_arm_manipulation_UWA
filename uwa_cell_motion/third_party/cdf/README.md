# CDF reference and attribution

Scientific reference: Yiming Li, Xuemin Chi, Amirreza Razmjoo, Sylvain Calinon,
*Configuration Space Distance Fields for Manipulation Planning*, RSS2024,
https://arxiv.org/abs/2406.01137 .

Reference implementation: https://github.com/yimingli1998/cdf , commit
`08a725718e748366c5b4da5cbc4c67e991961f0f` (MIT; license reproduced here).
Read on2026-11-16: `2Dexamples/cdf.py`, `frankaemika/data_generator.py`,
`frankaemika/qp_mp.py`, `readme.md`. Its QP structure, weighting and
contact-template algorithms inform this independent NumPy/SciPy UR adaptation.

No Franka assets/checkpoints, PyTorch/CasADi implementation or original source
module is imported at runtime. The source checkout under workspace
`setup/research/cdf-upstream/` is research data, not a ROS dependency.
UR adaptation/limitations are documented in `docs/single_ur_cdf.md` in the cell
repository. No claim of reproducing the neural Franka benchmarks is made.
