# La Amenaza Cuántica

La criptografía es la capa invisible que sustenta la seguridad en internet, permitiendo transacciones y comunicaciones privadas mediante barreras matemáticas.

## Protección de la Información

La información se protege mediante dos familias principales de criptografía:

*   **Criptografía simétrica:** Utiliza una única clave compartida por ambas partes, similar a una caja fuerte con una sola llave.
*   **Criptografía de clave pública (asimétrica):** Cada persona posee dos claves: una pública (compartida) y una privada (secreta). Esto permite establecer comunicaciones seguras entre partes que no se conocen previamente.

## Fundamentos Matemáticos de la Criptografía de Clave Pública

La seguridad de la criptografía de clave pública se basa en problemas matemáticos que son computacionalmente fáciles en una dirección, pero extremadamente difíciles de revertir para los ordenadores clásicos. Ejemplos incluyen:

*   **Multiplicación y factorización:** Multiplicar números grandes es sencillo, pero factorizar el resultado para obtener los números originales es casi imposible. Este principio es la base del algoritmo RSA.
*   **Logaritmo discreto:** Se apoya en la aritmética modular y es fundamental en protocolos como Diffie-Hellman.
*   **Curvas elípticas:** Permiten operaciones de inversión rápidas, ofreciendo alta seguridad con claves de menor tamaño y siendo ampliamente utilizadas en la actualidad.

## La Computación Cuántica

La dificultad de estos problemas matemáticos es relativa al tipo de ordenador utilizado.

### Diferencia entre Ordenadores Clásicos y Cuánticos

*   **Ordenadores clásicos:** Operan con bits (0 o 1).
*   **Ordenadores cuánticos:** Utilizan cúbits, que pueden representar combinaciones de estados simultáneamente y aprovechan propiedades físicas como la interferencia para amplificar las respuestas correctas. No son simplemente más rápidos, sino que emplean un modelo de cálculo distinto que altera la complejidad de ciertas categorías de problemas.

### El Algoritmo de Shor

En la década de 1990, se demostró teóricamente que un ordenador cuántico suficientemente potente podría resolver los problemas matemáticos que sustentan la criptografía de clave pública de manera eficiente mediante el algoritmo de Shor. Esto implica que la suposición de la imposibilidad de resolver estos problemas depende del uso de la computación clásica; un cambio en el modelo de computación modifica su dificultad.

La computación cuántica no representa un "atacante mejor", sino una categoría de capacidad computacional diferente que invalida los fundamentos actuales del sistema de confianza en internet.

## Consecuencias de la Amenaza Cuántica

La amenaza cuántica no requiere que la capacidad de computación cuántica esté disponible de inmediato para tener implicaciones actuales.

### El Riesgo de "Almacenar Ahora, Descifrar Después"

La información cifrada interceptada hoy puede ser almacenada por organizaciones o gobiernos con la intención de descifrarla en el futuro (10 o 20 años) cuando la computación cuántica sea una realidad. Este riesgo es particularmente relevante para datos con una vida útil prolongada, como información médica o financiera.

El riesgo comienza en el momento en que el dato es capturado, haciendo que la amenaza cuántica sea acumulativa y no instantánea.

### Vida Útil del Dato vs. Vida Útil del Algoritmo

Aunque existe incertidumbre sobre las fechas exactas para el desarrollo de ordenadores cuánticos capaces de romper la criptografía actual, el riesgo persiste. La seguridad de un dato se define por el tiempo que necesita ser protegido. Si la vida útil de un dato es mayor que la vida útil del algoritmo que lo protege, existe un problema de seguridad. La amenaza cuántica representa un cambio de paradigma que sugiere que lo que hoy es inaccesible podría volverse información abierta si el modelo de computación evoluciona.
