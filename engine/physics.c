#include <neweng/physics.h>

f64 NPhysics_cmsolver(f64 m1, f64 v1, f64 m2, f64 v2, f64 nv2) {
    return v1+(v2-nv2)*m2/m1; // Math is a strange thing.
}

void NPhysics_autocmsolver(f64 m1, f64 *v1, f64 m2, f64 *v2) {
   if (m1 < m2) {
        *v2 = NPhysics_cmsolver(m2, *v2, m1, *v1, -*v1);
        *v1 = -*v1;
    }
    if (m1 > m2) {
        *v1 = NPhysics_cmsolver(m1, *v1, m2, *v2, -*v2);
        *v2 = -*v2;
    }
}
