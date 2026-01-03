#pragma once
#include <neweng/main.h>

#ifndef DOT3
#define DOT3(x1,y1,z1,x2,y2,z2) (((x1)*(x2))+((y1)*(y2))+((z1)*(z2)))
#endif

f64 NPhysics_cmsolver(f64 m1, f64 v1, f64 m2, f64 v2, f64 nv2);

void NPhysics_autocmsolver(f64 m1, f64 *v1, f64 m2, f64 *v2);

