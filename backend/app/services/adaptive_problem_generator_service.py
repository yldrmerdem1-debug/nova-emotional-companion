from typing import Any


class AdaptiveProblemGeneratorService:
    def generate(self, domain: str, difficulty: int, previous: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        domain = domain.strip().casefold()
        difficulty = max(1, min(5, int(difficulty)))
        previous = previous or []
        seed = len(previous) + 1

        generators = {
            "cpp": self._cpp,
            "python": self._python,
            "java": self._java,
            "math": self._math,
            "physics": self._physics,
            "algorithms": self._algorithms,
        }
        generator = generators.get(domain, self._general)
        problem = generator(difficulty, seed)
        problem["id"] = f"{domain}_adaptive_d{difficulty}_{seed}"
        problem["domain"] = domain
        problem["difficulty"] = difficulty
        problem["source"] = "adaptive_generated"
        problem["training_stage"] = self._stage(difficulty)
        problem["olympiad_style"] = difficulty >= 4
        return problem

    def _stage(self, difficulty: int) -> str:
        if difficulty <= 1:
            return "general_foundation"
        if difficulty == 2:
            return "core_skill"
        if difficulty == 3:
            return "advanced_transfer"
        if difficulty == 4:
            return "olympiad_preparation"
        return "olympiad_challenge"

    def _cpp(self, difficulty: int, seed: int) -> dict[str, Any]:
        if difficulty <= 1:
            value = 2 + seed % 5
            return {
                "type": "generated_cpp_scope",
                "prompt": f"C++: int x={value}; x += 3; x kaç olur?",
                "expected": value + 3,
                "concepts": ["syntax", "assignment"],
                "explanation": f"x başlangıçta {value}; x += 3 sonrası {value + 3} olur.",
            }
        if difficulty == 2:
            base = 4 + seed % 6
            return {
                "type": "generated_cpp_reference",
                "prompt": f"C++: int x={base}; int& r=x; r*=2; x kaç olur?",
                "expected": base * 2,
                "concepts": ["references", "alias"],
                "explanation": f"r, x'in referansıdır; r*=2 işlemi x değerini {base * 2} yapar.",
            }
        if difficulty == 3:
            return {
                "type": "generated_cpp_complexity",
                "prompt": "C++: vector içinde baştan erase yapmak O(n) midir? Evet=1, Hayır=0.",
                "expected": 1,
                "concepts": ["vector", "complexity", "erase"],
                "explanation": "Baştan silmede sonraki elemanlar kaydırılır; bu yüzden işlem O(n) kabul edilir.",
            }
        if difficulty == 4:
            return {
                "type": "generated_cpp_dp",
                "prompt": "C++ olimpiyat hazırlığı: DP'de state yanlış tanımlanırsa doğru transition yeterli olur mu? Evet=1, Hayır=0.",
                "expected": 0,
                "concepts": ["dynamic_programming", "state", "proof"],
                "explanation": "State problemi yanlış temsil ederse transition doğru görünse bile çözüm yanlış modeli çözer.",
            }
        return {
            "type": "generated_cpp_olympiad_graph",
            "prompt": "C++ olimpiyat: Unweighted graph shortest path için priority_queue zorunlu mudur? Evet=1, Hayır=0.",
            "expected": 0,
            "concepts": ["graph", "bfs", "shortest_path"],
            "explanation": "Unweighted graph'ta BFS yeterlidir; priority_queue Dijkstra gibi ağırlıklı durumlar için gerekir.",
        }

    def _python(self, difficulty: int, seed: int) -> dict[str, Any]:
        if difficulty <= 1:
            values = [seed, seed + 1, seed + 2]
            total = sum(values)
            return {
                "type": "generated_python_list",
                "prompt": f"Python: nums={values}; sum(nums) kaçtır?",
                "expected": total,
                "concepts": ["lists", "sum"],
                "explanation": f"Liste toplamı {values[0]}+{values[1]}+{values[2]}={total}.",
            }
        if difficulty == 2:
            return {
                "type": "generated_python_dict",
                "prompt": "Python: dict key lookup average-case O(1) midir? Evet=1, Hayır=0.",
                "expected": 1,
                "concepts": ["dicts", "complexity"],
                "explanation": "Python dict hash table kullandığı için ortalama key lookup O(1) kabul edilir.",
            }
        if difficulty == 3:
            return {
                "type": "generated_python_generator",
                "prompt": "Python generator tüm değerleri baştan belleğe almak zorunda mıdır? Evet=1, Hayır=0.",
                "expected": 0,
                "concepts": ["generators", "yield", "memory"],
                "explanation": "Generator yield ile lazy üretir; tüm değerleri baştan belleğe almak zorunda değildir.",
            }
        if difficulty == 4:
            return {
                "type": "generated_python_recursion",
                "prompt": "Python olimpiyat hazırlığı: Memoization, recursive Fibonacci'de tekrar hesaplamayı azaltır mı? Evet=1, Hayır=0.",
                "expected": 1,
                "concepts": ["recursion", "memoization", "dynamic_programming"],
                "explanation": "Memoization aynı n değeri için sonucu saklar ve tekrar hesaplamayı azaltır.",
            }
        return {
            "type": "generated_python_invariant",
            "prompt": "Python olimpiyat: Binary search döngüsünde hedef varsa aralık içinde kalır invariantı korunmalı mıdır? Evet=1, Hayır=0.",
            "expected": 1,
            "concepts": ["binary_search", "invariant", "proof"],
            "explanation": "Binary search doğruluğu, hedef varsa güncel aralıkta kalması invariantına dayanır.",
        }

    def _java(self, difficulty: int, seed: int) -> dict[str, Any]:
        if difficulty <= 1:
            return {
                "type": "generated_java_string",
                "prompt": f"Java: \"robot{seed}\".length() sonucu kaçtır?",
                "expected": len(f"robot{seed}"),
                "concepts": ["strings", "methods"],
                "explanation": f"robot{seed} metninin karakter sayısı {len(f'robot{seed}')} olur.",
            }
        if difficulty == 2:
            return {
                "type": "generated_java_arraylist",
                "prompt": "Java ArrayList index ile erişimde average-case O(1) midir? Evet=1, Hayır=0.",
                "expected": 1,
                "concepts": ["arraylist", "complexity"],
                "explanation": "ArrayList dinamik array tabanlıdır; index erişimi ortalama O(1)'dir.",
            }
        if difficulty == 3:
            return {
                "type": "generated_java_polymorphism",
                "prompt": "Java'da interface üzerinden farklı implementasyonların çağrılması polymorphism midir? Evet=1, Hayır=0.",
                "expected": 1,
                "concepts": ["interfaces", "polymorphism", "oop"],
                "explanation": "Ortak interface üzerinden farklı davranışların çalışması polymorphism örneğidir.",
            }
        if difficulty == 4:
            if seed % 2 == 0:
                return {
                    "type": "generated_java_graph_degree",
                    "prompt": "Java olimpiyat hazırlığı: Undirected graph'ta degree toplamı 2E midir? Evet=1, Hayır=0.",
                    "expected": 1,
                    "concepts": ["graph", "proof", "algorithms"],
                    "explanation": "Her edge iki vertex derecesine katkı verir; bu yüzden derece toplamı 2E olur.",
                }
            return {
                "type": "generated_java_bfs",
                "prompt": "Java olimpiyat hazırlığı: BFS için Queue kullanmak doğru veri yapısı seçimi midir? Evet=1, Hayır=0.",
                "expected": 1,
                "concepts": ["queue", "bfs", "graph"],
                "explanation": "BFS FIFO sırayla katmanları gezer; Queue bu davranışa uygundur.",
            }
        if seed % 2 == 0:
            return {
                "type": "generated_java_dp",
                "prompt": "Java olimpiyat: DP çözümünde state tanımı yanlışsa kod hızlı olsa bile cevap yanlış olabilir mi? Evet=1, Hayır=0.",
                "expected": 1,
                "concepts": ["dynamic_programming", "state", "proof"],
                "explanation": "DP state problemi temsil eder; state yanlışsa hızlı kod yanlış problemi çözer.",
            }
        return {
            "type": "generated_java_greedy",
            "prompt": "Java olimpiyat: Greedy algoritmada sadece hızlı çalışması doğruluk kanıtı için yeterli midir? Evet=1, Hayır=0.",
            "expected": 0,
            "concepts": ["greedy", "proof_of_correctness"],
            "explanation": "Greedy için hız yetmez; exchange argument veya benzeri doğruluk kanıtı gerekir.",
        }

    def _math(self, difficulty: int, seed: int) -> dict[str, Any]:
        if difficulty <= 1:
            x = 2 + seed % 5
            return {
                "type": "generated_math_linear",
                "prompt": f"Matematik: 2x+4={2 * x + 4} ise x kaçtır?",
                "expected": x,
                "concepts": ["algebra", "linear_equation"],
                "explanation": f"2x={2 * x}, bu yüzden x={x}.",
            }
        if difficulty == 2:
            n = 5 + seed % 5
            return {
                "type": "generated_math_series",
                "prompt": f"Matematik: 1+2+...+{n} toplamı kaçtır?",
                "expected": n * (n + 1) // 2,
                "concepts": ["series", "formula"],
                "explanation": f"n(n+1)/2 formülünde n={n}; sonuç {n * (n + 1) // 2}.",
            }
        if difficulty == 3:
            return {
                "type": "generated_math_function",
                "prompt": "Fonksiyon: f(x)=2x+1, g(x)=x^2 ise f(g(3)) kaçtır?",
                "expected": 19,
                "concepts": ["functions", "composition"],
                "explanation": "g(3)=9 ve f(9)=2*9+1=19.",
            }
        if difficulty == 4:
            base = 9 + (seed % 5)
            modulus = 5 + (seed % 4)
            expected = pow(base, 2, modulus)
            return {
                "type": "generated_math_modular",
                "prompt": f"Olimpiyat matematik: {base}^2 mod {modulus} kaçtır?",
                "expected": expected,
                "concepts": ["number_theory", "modular_arithmetic"],
                "explanation": f"{base}^2={base * base}; {base * base} mod {modulus} = {expected}.",
            }
        coefficient = 1 + seed % 4
        return {
            "type": "generated_math_inequality",
            "prompt": f"Olimpiyat matematik: Pozitif x için x+{coefficient}/x >= 2*sqrt({coefficient}) her zaman doğru mudur? Evet=1, Hayır=0.",
            "expected": 1,
            "concepts": ["inequalities", "am_gm", "proof"],
            "explanation": f"AM-GM ile x ve {coefficient}/x pozitif olduğundan toplam en az 2*sqrt({coefficient}) olur.",
        }

    def _physics(self, difficulty: int, seed: int) -> dict[str, Any]:
        if difficulty <= 1:
            distance = 20 + seed * 2
            time = 2
            return {
                "type": "generated_physics_velocity",
                "prompt": f"Fizik: {time} saniyede {distance} metre giden cismin ortalama hızı kaç m/s olur?",
                "expected": distance // time,
                "concepts": ["kinematics", "velocity", "units"],
                "explanation": f"Ortalama hız yol/zaman = {distance}/{time} = {distance // time} m/s.",
            }
        if difficulty == 2:
            return {
                "type": "generated_physics_energy",
                "prompt": "Fizik: m=2 kg, v=4 m/s ise kinetik enerji kaç Joule olur? KE=1/2mv^2.",
                "expected": 16,
                "concepts": ["energy", "kinetic_energy"],
                "explanation": "KE=1/2*2*4^2=16 Joule.",
            }
        if difficulty == 3:
            return {
                "type": "generated_physics_circuit",
                "prompt": "Fizik: V=18 V, R=6 ohm ise I=V/R kaç amperdir?",
                "expected": 3,
                "concepts": ["electricity", "ohm_law"],
                "explanation": "Ohm kanununa göre I=18/6=3 amper.",
            }
        if difficulty == 4:
            angle = "yatay" if seed % 2 == 0 else "düşey"
            expected = 1 if angle == "yatay" else 0
            return {
                "type": "generated_physics_projectile",
                "prompt": f"Fizik olimpiyat hazırlığı: Hava direnci yoksa yatay atışta {angle} ivme sıfır mıdır? Evet=1, Hayır=0.",
                "expected": expected,
                "concepts": ["kinematics", "vectors"],
                "explanation": "Hava direnci yoksa yatay ivme sıfırdır; düşey yönde yerçekimi ivmesi vardır.",
            }
        mass = 2 + seed % 4
        velocity = 3 + seed % 5
        return {
            "type": "generated_physics_conservation",
            "prompt": f"Fizik olimpiyat: {mass} kg cisim {velocity} m/s hızla gidiyorsa momentumu kaç kg*m/s olur?",
            "expected": mass * velocity,
            "concepts": ["momentum", "conservation", "proof"],
            "explanation": f"Momentum p=m*v={mass}*{velocity}={mass * velocity} kg*m/s.",
        }

    def _algorithms(self, difficulty: int, seed: int) -> dict[str, Any]:
        if difficulty <= 1:
            return {
                "type": "generated_algo_stack",
                "prompt": "Algoritma: Stack'e 4,5,6 push edilirse ilk pop sonucu kaçtır?",
                "expected": 6,
                "concepts": ["stack", "lifo"],
                "explanation": "Stack LIFO çalışır; son giren 6 ilk çıkar.",
            }
        if difficulty == 2:
            return {
                "type": "generated_algo_binary_search",
                "prompt": "Algoritma: Sorted array [2,4,6,8,10] içinde 8 binary search ile bulunabilir mi? Evet=1, Hayır=0.",
                "expected": 1,
                "concepts": ["binary_search", "search"],
                "explanation": "Dizi sıralıdır; binary search 8'i aralık daraltarak bulabilir.",
            }
        if difficulty == 3:
            return {
                "type": "generated_algo_dp",
                "prompt": "Algoritma: DP'de overlapping subproblems yoksa memoization her zaman büyük kazanç sağlar mı? Evet=1, Hayır=0.",
                "expected": 0,
                "concepts": ["dynamic_programming", "overlapping_subproblems"],
                "explanation": "Memoization en çok aynı alt problemler tekrarlandığında kazanç sağlar.",
            }
        if difficulty == 4:
            property_name = "toplam" if seed % 2 == 0 else "parite"
            return {
                "type": "generated_algo_invariant",
                "prompt": f"Olimpiyat algoritma: Döngü boyunca {property_name} değişmiyorsa bu invariant olarak kullanılabilir mi? Evet=1, Hayır=0.",
                "expected": 1,
                "concepts": ["invariant", "proof_of_correctness"],
                "explanation": f"Döngü boyunca korunan {property_name} özelliği invariant olarak doğruluk kanıtına bağlanabilir.",
            }
        technique = "exchange argument" if seed % 2 == 0 else "cut property"
        return {
            "type": "generated_algo_greedy",
            "prompt": f"Olimpiyat algoritma: Greedy seçimin optimal olduğunu göstermek için {technique} kullanılabilir mi? Evet=1, Hayır=0.",
            "expected": 1,
            "concepts": ["greedy", "proof_of_correctness"],
            "explanation": f"{technique}, greedy seçimin optimal çözümle uyumlu olduğunu kanıtlamak için kullanılabilir.",
        }

    def _general(self, difficulty: int, seed: int) -> dict[str, Any]:
        return {
            "type": "generated_general",
            "prompt": f"Genel bilgi: {seed}+{difficulty} kaçtır?",
            "expected": seed + difficulty,
            "concepts": ["general"],
            "explanation": f"{seed}+{difficulty}={seed + difficulty}.",
        }


adaptive_problem_generator_service = AdaptiveProblemGeneratorService()
