#include <zeminka/physics.h>

void ZEPhysics_cmsolver(f64 m1, ZEVec3 *v1, f64 m2, ZEVec3 *v2, ZEVec3 o1, ZEVec3 o2) {
    // WTF?
    *v1 = ZEVec3_Add(*v1, ZEVec3_Scale(o1, 1/m1));
    *v2 = ZEVec3_Add(*v2, ZEVec3_Scale(o2, 1/m2));
}
