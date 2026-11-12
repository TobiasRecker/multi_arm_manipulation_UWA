"""Operator-authorized independent diagonal hardware motion (2026-11-12).

Reach separation is the user's physical-cell statement, not a measured result.
Only the two named opposite-corner pairs are exempted; all other collisions stay.
"""
import xml.etree.ElementTree as ET

DIAGONAL = {'left_front':'right_rear','right_rear':'left_front',
            'left_rear':'right_front','right_front':'left_rear'}


def independent_arm(plan):
    partner=plan.get('independent_diagonal_arm')
    if partner is not None and partner!=DIAGONAL.get(plan['arm']):
        raise ValueError('Independent motion exemption is only valid for the diagonal arm')
    return partner


def configure_model(model, arm, partner):
    if partner!=DIAGONAL.get(arm):
        raise ValueError('Only the explicitly authorized diagonal pair may be excluded')
    names=[link.get('name') for link in ET.fromstring(model.description).findall('link')]
    prefix=getattr(model,'prefix','')
    first=[n for n in names if n.startswith(prefix+arm+'_')]
    second=[n for n in names if n.startswith(prefix+partner+'_')]
    if not first or not second:raise ValueError('Diagonal arm links missing from collision model')
    for a in first:
        for b in second:model.scene.allowed_collision_matrix.set_entry(a,b,True)
