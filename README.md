# AGI 발현을 위한 메타인지 프레임워크 핵심기술 개발 및 실증
## AGI 발현을 위한 Planner에 대한 연구 개발
### 입력 프롬프트를 최적으로 처리하기 위한 Open-ended, Closed-ended 프롬프트 모듈 라이브러리

### 💡 예시
- 외부 지식이 필요한 Open-ended 문제의 경우, RAG 기반 지식 보강 모듈과 함께 문제 해결에 필요한 프롬프트 모듈을 선택
![image](image/ex_open_ended.png)

- 내부 지식만으로 해결 가능한 Closed-ended 문제의 경우, RAG 모듈 없이 문제 해결에 필요한 프롬프트 모듈만 선택
![image](image/ex_closed_ended.png)

## ⚙️ Requirements
```
pip install -r requirements.txt
```

## 💻 Usage Guide
### 1. Dataset 준비
- 자세한 내용은 [README.md](data/README.md)를 참고해주세요.

### 2. 입력 프롬프트에 적합한 모듈 라이브러리 선택
```
python src/generation.py --dataset_name "dataset_name" --model_name "model_name"
```

## 🧠 작동 원리
**1️⃣ open-ended 문제 처리를 위한 프롬프트 모듈 라이브러리 확장** \
모델의 내재된 지식만으로 해결 가능한 closed-ended 문제와 달리, open-ended 문제는 외부 지식의 보강이 필요할 수 있습니다. \
이때 모델이 스스로 외부 지식의 필요성을 판단하도록 하기 위해, 다음과 같은 모듈을 프롬프트 라이브러리에 추가합니다: \
```Check if retrieval from external sources is needed to answer the question.``` \
이를 통해 모델은 입력된 문제의 특성에 따라 외부 검색(retrieval) 여부를 자율적으로 결정할 수 있습니다.

**2️⃣ 프롬프트 모듈 선택** \
입력 프롬프트와 함께 제공된 open-ended / closed-ended 모듈 라이브러리 중에서, \
모델은 주어진 입력을 처리하기에 가장 적합하다고 판단되는 모듈을 선택하여 활용합니다.

**💡 장점**
- 모델이 입력 프롬프트의 특성을 분석하여 스스로 필요한 모듈을 선택함으로써, 문제 해결 효율성을 높일 수 있습니다.
- closed-ended 문제뿐 아니라, 외부 지식 보강 필요 여부를 자동으로 판단하여 open-ended 문제에도 유연하게 대응할 수 있습니다.


### Reference
[Promptbreeder: Self-Referential Self-Improvement Via Prompt Evolution](https://arxiv.org/pdf/2309.16797)
```
@article{fernando2023promptbreeder,
  title={Promptbreeder: Self-referential self-improvement via prompt evolution},
  author={Fernando, Chrisantha and Banarse, Dylan and Michalewski, Henryk and Osindero, Simon and Rockt{\"a}schel, Tim},
  journal={arXiv preprint arXiv:2309.16797},
  year={2023}
}
```
