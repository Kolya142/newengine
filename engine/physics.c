#include <zeminka/physics.h>

void ZEPhysics_cmsolver(f64 m1, ZEVec3 *v1, f64 m2, ZEVec3 *v2) {
    // WTF?
    
    // m1, m2 - masses.
    // v1, v2 - velocities.

    ZEVec3 bv1 = *v1,
        bv2 = *v2;

    *v1 = ZEVec3_Add(ZEVec3_Scale(ZEVec3_Sub(bv2, *v1), m2/m1), *v1);
    *v2 = ZEVec3_Add(ZEVec3_Scale(ZEVec3_Sub(bv1, *v2), m1/m2), *v2);

    // C=m1*v1+m2*v2
}
