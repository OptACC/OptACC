#include <stdio.h>
#include <stdlib.h>
#include <omp.h>

#define SIZE 1048576

int main() {
    double *A = (double *)malloc(sizeof(double) * SIZE);
    double t_start, t_end;
    #pragma acc data copyin(A[0:SIZE])
    {
        t_start = omp_get_wtime();
        #pragma acc parallel loop num_gangs(NUM_GANGS), vector_length(VECTOR_LENGTH)
        for (int i = 0; i < SIZE; i++) {
            A[i] = i * i;
        }
        t_end = omp_get_wtime();
    }

    /* missing timing data */
    return 0;
}
