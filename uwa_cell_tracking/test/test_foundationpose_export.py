"""Run in .venvs/oak-model; verify frame independence and RGB-D resampling."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
try:
    import numpy as np
    from PIL import Image
    spec = importlib.util.spec_from_file_location('fp_prepare', ROOT / 'tools/foundationpose_prepare_input.py')
    prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepare)
except ImportError:
    prepare = None


@unittest.skipIf(prepare is None, 'Run with the oak-model Python environment')
class InputExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.asset = ROOT / 'uwa_cell_description/assets/carton_avocado_v1'

    def test_stored_scene_pose_cannot_move_exported_model(self):
        source = self.root / 'asset'
        shutil.copytree(self.asset, source)
        first = prepare.export_model(source, self.root / 'model1')
        manifest = json.loads((source / 'asset.json').read_text())
        manifest['reference_pose'] = {'T_frame_object': [[12345] * 4] * 4}
        (source / 'asset.json').write_text(json.dumps(manifest))
        second = prepare.export_model(source, self.root / 'model2')
        np.testing.assert_array_equal(first['bounds'], second['bounds'])
        np.testing.assert_array_equal(first['dimensions_m'], second['dimensions_m'])
        self.assertEqual(first['triangles'], second['triangles'])
        self.assertFalse(second['scene_pose_used'])

    def fixture(self, wrong_hash=False):
        capture = self.root / 'capture'
        (capture / 'rgb').mkdir(parents=True)
        (capture / 'depth').mkdir()
        Image.new('RGB', (32, 24), (120, 80, 50)).save(capture / 'rgb/0.png')
        depth = np.arange(32 * 24, dtype=np.uint16).reshape(24, 32) + 1000
        depth[:, :5] = 0
        Image.fromarray(depth).save(capture / 'depth/0.png')
        k = [[500., 0., 16.], [0., 500., 12.], [0., 0., 1.]]
        metadata = dict(success=True, kind='rgbd', max_timestamp_difference_s=.025,
            projection=dict(K=k, depth_K=k, D=[0] * 5, size=[32, 24]),
            pairs=[dict(rgb_path='rgb/0.png', depth_path='depth/0.png', timestamp_difference_s=.002)])
        (capture / 'metadata.json').write_text(json.dumps(metadata))
        annotation = self.root / 'mask.json'
        annotation.write_text(json.dumps(dict(image_size=[32, 24], source_frame=0,
            source_rgb_sha256='wrong' if wrong_hash else prepare.sha(capture / 'rgb/0.png'),
            outer_polygon=[[0, 0], [31, 0], [31, 23], [0, 23]])))
        return capture, annotation, depth

    def test_reduction_preserves_mm_depth_and_invalid_pixels(self):
        capture, annotation, depth = self.fixture()
        output = self.root / 'input'
        with patch.object(sys, 'argv', ['prepare', '--asset', str(self.asset), '--capture', str(capture),
             '--mask-annotation', str(annotation), '--output', str(output), '--downsample', '2']), \
             patch('builtins.print'):
            prepare.main()
        reduced = np.asarray(Image.open(output / 'depth/000000.png'))
        self.assertEqual(reduced.dtype, np.uint16)
        np.testing.assert_array_equal(reduced, depth[1::2, 1::2])
        np.testing.assert_allclose(np.loadtxt(output / 'cam_K.txt'),
                                   [[250., 0., 7.75], [0., 250., 5.75], [0., 0., 1.]])
        self.assertFalse(json.loads((output / 'input.json').read_text())['manipulation_approved'])

    def test_mask_for_different_color_frame_is_rejected(self):
        capture, annotation, _ = self.fixture(wrong_hash=True)
        output = self.root / 'input'
        with patch.object(sys, 'argv', ['prepare', '--asset', str(self.asset), '--capture', str(capture),
             '--mask-annotation', str(annotation), '--output', str(output)]):
            with self.assertRaisesRegex(ValueError, 'first RGB payload'):
                prepare.main()
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
