# SQL 기본

## SQL 문장의 종류
DML(데이터 조작어)에는 SELECT, INSERT, UPDATE, DELETE, MERGE가 있다. DDL(데이터 정의어)에는 CREATE, ALTER, DROP, RENAME, TRUNCATE가 있다. DCL(데이터 제어어)에는 GRANT, REVOKE가 있다. TCL(트랜잭션 제어어)에는 COMMIT, ROLLBACK, SAVEPOINT가 있다.

## DELETE, TRUNCATE, DROP 비교
DROP은 테이블의 데이터와 구조를 모두 삭제하며 롤백할 수 없다.
TRUNCATE는 테이블 구조는 남기고 모든 데이터를 삭제하며, DDL이므로 자동 커밋되어 롤백할 수 없다. 저장 공간도 해제된다.
DELETE는 DML이므로 커밋 전에는 롤백할 수 있고, WHERE 절로 일부 행만 삭제할 수 있다. 데이터를 지워도 테이블이 사용하던 저장 공간은 해제되지 않는다.

## 제약조건
PRIMARY KEY는 테이블에 저장된 행을 고유하게 식별하며 NULL과 중복값을 허용하지 않는다. 하나의 테이블에 하나만 정의할 수 있다.
UNIQUE KEY는 중복값을 허용하지 않지만 NULL은 허용한다.
NOT NULL은 NULL 값 입력을 금지한다. CHECK는 입력 가능한 값의 범위를 제한한다.
FOREIGN KEY는 다른 테이블의 기본키를 참조하는 외래키로, 참조 무결성을 보장한다. 외래키는 NULL을 가질 수 있다.
참조 무결성 옵션 중 CASCADE는 부모 행이 삭제되면 자식 행도 함께 삭제하고, SET NULL은 자식의 외래키 값을 NULL로 바꾸며, RESTRICT는 자식 행이 있으면 부모 행의 삭제를 막는다.

## SELECT 문의 실행 순서
SELECT 문은 FROM, WHERE, GROUP BY, HAVING, SELECT, ORDER BY 순서로 실행된다. 그래서 SELECT 절에서 정의한 별칭은 WHERE 절에서는 사용할 수 없지만 ORDER BY 절에서는 사용할 수 있다.

## NULL의 특성
NULL은 아직 정의되지 않은 값으로, 0이나 공백과는 다르다. NULL과의 산술 연산 결과는 NULL이다. NULL과의 비교 연산 결과는 알 수 없음(Unknown)이며, 조건절에서 거짓처럼 처리된다. 따라서 NULL 여부를 확인할 때는 = NULL이 아니라 IS NULL을 사용해야 한다.
집계 함수는 NULL을 제외하고 계산한다. 예를 들어 COUNT(컬럼)은 NULL이 아닌 행만 세지만, COUNT(*)는 NULL을 포함한 전체 행 수를 센다. AVG 역시 NULL인 행을 분모에서 제외한다.

## NULL 관련 함수
NVL(표현식1, 표현식2)은 표현식1이 NULL이면 표현식2를 반환한다. SQL Server에서는 ISNULL 함수가 같은 역할을 한다.
NULLIF(표현식1, 표현식2)는 두 값이 같으면 NULL을, 다르면 표현식1을 반환한다.
COALESCE(표현식1, 표현식2, ...)는 NULL이 아닌 첫 번째 표현식을 반환한다.
NVL2(표현식1, 표현식2, 표현식3)는 표현식1이 NULL이 아니면 표현식2를, NULL이면 표현식3을 반환한다.

## 단일행 함수
문자 함수에는 LOWER, UPPER, SUBSTR, LENGTH, LTRIM, RTRIM, TRIM, CONCAT 등이 있다. 숫자 함수에는 ROUND, TRUNC, CEIL, FLOOR, MOD, ABS, SIGN 등이 있다. CEIL은 크거나 같은 최소 정수를, FLOOR는 작거나 같은 최대 정수를 반환한다.
CASE 표현식은 IF-THEN-ELSE 논리를 SQL에서 구현한다. Oracle의 DECODE 함수도 비슷한 역할을 한다.

## WHERE 절 연산자
BETWEEN a AND b는 a 이상 b 이하의 값을 찾으며 양 끝 값을 포함한다. IN (리스트)은 리스트 안의 값 중 하나와 일치하면 참이다. LIKE 연산자에서 %는 0개 이상의 문자를, _는 정확히 한 개의 문자를 의미한다.
연산자 우선순위는 괄호, 비교 연산자, NOT, AND, OR 순이다. 즉 AND가 OR보다 먼저 처리된다.

## GROUP BY와 HAVING
GROUP BY 절은 행들을 소그룹으로 나누고, HAVING 절은 GROUP BY로 만들어진 그룹에 조건을 건다. WHERE 절에는 집계 함수를 사용할 수 없으므로, 집계 결과에 대한 조건은 HAVING 절에 작성해야 한다.
GROUP BY를 사용할 때 SELECT 절에는 GROUP BY에 사용한 컬럼이나 집계 함수만 올 수 있다.

## ORDER BY
ORDER BY는 결과를 정렬하며 기본값은 오름차순(ASC)이다. Oracle은 NULL을 가장 큰 값으로 취급해 오름차순에서 마지막에 오고, SQL Server는 NULL을 가장 작은 값으로 취급해 오름차순에서 처음에 온다.

## 트랜잭션
트랜잭션은 데이터베이스의 논리적인 작업 단위로, 원자성, 일관성, 고립성, 지속성의 네 가지 특성(ACID)을 가진다. 원자성은 트랜잭션의 연산이 모두 성공하거나 모두 실패해야 한다는 것이다. 일관성은 트랜잭션 실행 전후에 데이터베이스가 일관된 상태여야 한다는 것이다. 고립성은 실행 중인 트랜잭션의 중간 결과에 다른 트랜잭션이 접근할 수 없다는 것이다. 지속성은 성공적으로 완료된 트랜잭션의 결과가 영구적으로 저장된다는 것이다.
SAVEPOINT는 트랜잭션 중간에 저장점을 지정해, ROLLBACK TO 저장점으로 그 지점까지만 되돌릴 수 있게 한다.
Oracle은 DDL 문장을 실행하면 자동으로 커밋되는 반면, SQL Server는 기본적으로 AUTO COMMIT 모드로 동작한다.
트랜잭션 고립성이 지켜지지 않을 때 발생하는 문제로는 Dirty Read, Non-Repeatable Read, Phantom Read가 있다. Dirty Read는 다른 트랜잭션이 수정하고 아직 커밋하지 않은 데이터를 읽는 것이다. Non-Repeatable Read는 한 트랜잭션 안에서 같은 쿼리를 두 번 실행했을 때 그 사이에 다른 트랜잭션이 값을 수정해 결과가 달라지는 것이다. Phantom Read는 같은 조건으로 두 번 조회했을 때 첫 번째 조회에 없던 행이 새로 나타나는 것이다.
