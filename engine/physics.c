#include <zeminka/physics.h>

f64 ZEPhysics_cmsolver(f64 m1, f64 v1, f64 m2, f64 v2, f64 nv2) {
    return v1+(v2-nv2)*m2/m1; // Math is a strange thing.
}

#include <stdio.h>

// My desmos graph about angular velocity, not actually the same but kinda the same - https://www.desmos.com/calculator/rusvgepsgl.
ZEVec3 ZEPhysics_get_vel(f64 m, ZEVec3 v0, ZEVec3 f, f64 d) {
    f64 x = v0.x-f.x/d/m;
    f64 y = v0.y-f.y/d/m;
    f64 z = v0.z-f.z/d/m;
    printf("ZEPGV(%2.2f, %2.2f;%2.2f;%2.2f, %2.2f;%2.2f;%2.2f, %2.2f) = %2.2f;%2.2f;%2.2f\n", m, v0.x, v0.y, v0.z, f.x, f.y, f.z, d, x, y, z);
    return ZEVec3_From3(x, y, z);
}

void ZEPhysics_autocmsolver(f64 m1, f64 *v1, f64 m2, f64 *v2) {
   if (m1 < m2) {
        *v2 = ZEPhysics_cmsolver(m2, *v2, m1, *v1, -*v1);
        *v1 = -*v1;
    }
    if (m1 > m2) {
        *v1 = ZEPhysics_cmsolver(m1, *v1, m2, *v2, -*v2);
        *v2 = -*v2;
    }
}
