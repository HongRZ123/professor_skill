# 编程课的语言怎样带人跟上执行

Ana Bell 的第二、第四课显示，初学编程的讲述经常在日常语言与精确的执行含义之间来回移动。这里比较的是她实际做的几段解释，而非为编程课拟定一个统一格式。

第二课用寻找免费食物的迷宫情境谈选择和重复。关键不只在故事有趣：Bell 随后回指自己刚用过的英语条件词，让学生注意日常描述中已有的分支结构。她还修正“计算机作决定”可能带来的误解，把行为重新归到程序员写下的条件。[官方第二课](https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/resources/lecture-2-branching-and-iteration/)，研究定位 M-BE02 B016–B019，时间约 16:04–19:44。

第四课的起点换了。学生已经写过一段段可以工作的代码，她承认这种写法在小程序里可行，再谈复制、修改和组织变得困难的地方。她用投影仪说明使用某种功能与理解内部构造的区别，又借多个投影仪谈分解。比喻处理的是此刻出现的组织问题。[官方第四课](https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/resources/lecture-4-decomposition-abstraction-and-functions/)，研究定位 M-BE04 B001–B008。

到函数调用的选段，她先说：“I don't care what's inside the function definition yet, because I haven't called the function yet.” 两个 yet 把暂不阅读函数体的理由系在执行时机上。随后讲述转到“我们现在到哪里、返回以后发生什么”。处理 `print` 与 `return` 时，她追踪执行差别，而非只把两个定义并排放置；学生指出一个表述问题后，她也修正并重说。M-BE04 B020–B023。

我认为，这些话的价值在于帮助读者切换关注对象：代码写在什么位置，与程序现在执行到哪里，并非同一回事。静态阅读源码时尤其容易把二者混在一起。但不能据此要求每节计算机课都画执行轨迹；讲接口取舍、系统演化或算法证明时，注意力可能不沿执行时间组织。

## 换一位教师，也换一个课程阶段

Devadas 的算法第一课已经能够让输入规模、候选算法和失败情形承担大段解释。学生追问使问题规格更明确；一个二维推广中看似有希望的方法又迫使讨论回到正确性。[官方课堂](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-fall-2011/resources/lecture-1-algorithmic-thinking-peak-finding/)，研究定位 M-D01 PDF 第七至十九页。

与 Bell 的差别不宜全归因于教师个性：入门程序设计与算法课程拥有不同前提。可以留下的经验，是怎样利用学生已经会做的事引出新的困难，以及语言何时跟随执行、何时离开执行去谈整体性质。原课堂的迷宫简化、函数作用域的口头比喻和历史性能例子，都需要另行核对才可作为新课的知识内容。
