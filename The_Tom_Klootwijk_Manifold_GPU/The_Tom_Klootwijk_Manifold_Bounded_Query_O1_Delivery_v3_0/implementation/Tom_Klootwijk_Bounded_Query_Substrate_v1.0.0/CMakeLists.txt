cmake_minimum_required(VERSION 3.24)
project(tom_klootwijk_bounded_query_substrate VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(TKM_BUILD_CUDA "Build the optional CUDA smoke test when a CUDA compiler is available" ON)
set(TKM_CUDA_ARCH "native" CACHE STRING "CMake CUDA architecture list, for example native or 120")

add_library(tkm INTERFACE)
target_include_directories(tkm INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_compile_features(tkm INTERFACE cxx_std_20)

add_executable(tkm_demo src/demo.cpp)
target_link_libraries(tkm_demo PRIVATE tkm)

if(MSVC)
    target_compile_options(tkm_demo PRIVATE /W4 /permissive-)
else()
    target_compile_options(tkm_demo PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow)
endif()

include(CTest)
if(BUILD_TESTING)
    add_executable(tkm_tests tests/test_tkm.cpp)
    target_link_libraries(tkm_tests PRIVATE tkm)
    if(MSVC)
        target_compile_options(tkm_tests PRIVATE /W4 /permissive-)
    else()
        target_compile_options(tkm_tests PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow)
    endif()
    add_test(NAME tkm_bounded_query_tests COMMAND tkm_tests)
endif()

if(TKM_BUILD_CUDA)
    include(CheckLanguage)
    check_language(CUDA)
    if(CMAKE_CUDA_COMPILER)
        enable_language(CUDA)
        add_executable(tkm_cuda_smoke src/cuda_query.cu)
        target_link_libraries(tkm_cuda_smoke PRIVATE tkm)
        set_target_properties(tkm_cuda_smoke PROPERTIES
            CUDA_STANDARD 20
            CUDA_STANDARD_REQUIRED ON
            CUDA_EXTENSIONS OFF
            CUDA_ARCHITECTURES "${TKM_CUDA_ARCH}"
        )
        target_compile_options(tkm_cuda_smoke PRIVATE
            $<$<COMPILE_LANGUAGE:CUDA>:--generate-line-info>
        )
    else()
        message(STATUS "CUDA compiler not found: building CPU reference and tests only")
    endif()
endif()
