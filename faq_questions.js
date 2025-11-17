// faq_questions.js - Quinnipiac University Real FAQs

const faqQuestions = [
  {
    
    category: "Student Experience and Residential Life",
    question: "What percentage of students live on campus?",
    answer: "Approximately 5,000 undergraduate students (72%) live in campus-owned properties; 95% of first-year students live on campus.",
    keywords: ["live on campus", "housing", "percentage", "undergraduate"]
  },
  {
    
    category: "Student Experience and Residential Life",
    question: "Are first-year students required to live on campus?",
    answer: "Yes. New first-year students are required to live in campus housing for their first 3 years of study.",
    keywords: ["first-year", "required", "housing", "dorm", "live on campus"]
  },
  {
    
    category: "Student Experience and Residential Life",
    question: "Is housing guaranteed for all 4 years?",
    answer: "Housing is guaranteed for the first 3 years and offered on a space-available basis in the senior year.",
    keywords: ["housing", "guarantee", "four years", "senior"]
  },
  {
    
    category: "Student Experience and Residential Life",
    question: "Can first-year students have cars on campus?",
    answer: "First-year residential students are not permitted to have cars. Free shuttle service is available.",
    keywords: ["car", "vehicle", "first-year", "transportation", "shuttle"]
  },
  {
    
    category: "Student Experience and Residential Life",
    question: "What is the first-year student class distribution?",
    answer: "About 1,800 students from 30+ states and 20+ countries with an average GPA of 3.4.",
    keywords: ["class profile", "first-year", "GPA", "distribution"]
  },
  {
    
    category: "Student Experience and Residential Life",
    question: "What activities are available on and off campus?",
    answer: "Over 140 clubs, intramurals, Division I athletics, arts, events, and free shuttle access to nearby areas.",
    keywords: ["activities", "clubs", "sports", "events", "shuttle"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "What is the cost of tuition, fees, room and board?",
    answer: "Tuition, fees, room and board details can be found on the university's official Costs and Budgets page. Quinnipiac is committed to helping you explore ways of financing your education.",
    keywords: ["tuition", "cost", "fees", "room and board", "budgets"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "How do I apply for financial aid?",
    answer: "File the FAFSA (Free Application for Federal Student Aid) on or after it opens and before March 1. Quinnipiac’s FAFSA code is 001402.",
    keywords: ["financial aid", "FAFSA", "apply", "federal aid", "001402"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "Are scholarships offered and how do I apply?",
    answer: "There is no separate application required for academic scholarships. Scholarship awards are included in the acceptance letter.",
    keywords: ["scholarship", "aid", "merit", "apply", "award"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "When will I hear about financial aid or scholarships?",
    answer: "Financial aid awards are sent separately after acceptance. Merit scholarships are listed on the acceptance letter.",
    keywords: ["financial aid", "scholarship notification", "award", "acceptance"]
  },

  {
    
    category: "Admissions Requirements and Application Process",
    question: "Am I required to take certain high school subjects?",
    answer: "Quinnipiac looks for at least 16 college preparatory academic courses including English, math, science, social science, and a language. Health sciences and nursing require 4 years of math and science.",
    keywords: ["high school courses", "requirements", "math", "science", "preparatory"]
  },
  {
    
    category: "Admissions Requirements and Application Process",
    question: "Do you accept AP, IB, or college courses for credit?",
    answer: "AP exam scores with the required minimum earn credit. HL IB courses with a score of 4 or higher also earn credit. College courses taken during high school may also transfer.",
    keywords: ["AP", "IB", "college credit", "transfer", "scores"]
  },
  {
    
    category: "Admissions Requirements and Application Process",
    question: "When is the application deadline?",
    answer: "Early Decision: November 1, Early Action: November 15, Regular Decision: February 1. FAFSA priority deadline is March 1.",
    keywords: ["application deadline", "early action", "regular decision", "dates"]
  },
  {
    
    category: "Admissions Requirements and Application Process",
    question: "Do Early Decision applicants have a better chance of being accepted?",
    answer: "No. Early Decision does not improve admission chances. It is binding and should only be chosen if the student is ready to commit.",
    keywords: ["early decision", "ED", "acceptance", "binding", "admissions"]
  },
  {
    
    category: "Admissions Requirements and Application Process",
    question: "Which standardized tests do you accept and are they required?",
    answer: "Quinnipiac provides a full testing policy online. Some programs may require test scores, but many are test-optional.",
    keywords: ["SAT", "ACT", "test optional", "standardized tests"]
  },
  {
    
    category: "Admissions Requirements and Application Process",
    question: "Will you accept self-reported test scores?",
    answer: "Yes. Self-reported test scores are accepted for application review, but official scores must be provided before enrollment.",
    keywords: ["self-reported", "test scores", "SAT", "ACT"]
  },
  {
    
    category: "Admissions Requirements and Application Process",
    question: "What are the average GPA and test scores for admitted first-year students?",
    answer: "Strong applicants typically have a GPA of around 3.3 or higher, SAT scores between 1080–1300, or ACT scores between 22–28.",
    keywords: ["GPA", "SAT", "ACT", "admitted students", "average scores"]
  },
  {
    
    category: "Admissions Requirements and Application Process",
    question: "Are recommendations, an interview, or an essay required?",
    answer: "A personal essay and one letter of recommendation are required. Interviews are optional but available.",
    keywords: ["essay", "recommendation", "interview", "requirements"]
  },
  {
    
    category: "Admissions Requirements and Application Process",
    question: "How and when will I be notified of an admission decision?",
    answer: "Applicants can check their status online. Decision release dates vary by application type (ED, EA, RD).",
    keywords: ["decision", "notification", "admissions status", "timeline"]
  },

  {
    
    category: "Academics",
    question: "Does Quinnipiac offer an honors program?",
    answer: "Yes. Students can apply to the Honors Program after being admitted. About 80–100 first-year students are selected yearly.",
    keywords: ["honors program", "academics", "apply", "honors"]
  },
  {
    
    category: "Academics",
    question: "What if I am not sure which major I want?",
    answer: "Students may enter as undeclared in liberal arts, business, communications, engineering, natural sciences, or health sciences.",
    keywords: ["undeclared", "major", "choosing a major"]
  },
  {
    
    category: "Academics",
    question: "When do I need to declare a major?",
    answer: "Students typically declare a major by the end of sophomore year. Some programs may not allow internal transfers.",
    keywords: ["declare major", "sophomore", "advising"]
  },
  {
    
    category: "Academics",
    question: "What study away or study abroad options are available?",
    answer: "Students can study abroad for a semester in many countries or join faculty-led travel programs. Domestic options include QU in LA and Washington, D.C.",
    keywords: ["study abroad", "study away", "international", "domestic programs"]
  },
  {
    
    category: "Academics",
    question: "What types of internships or clinical experiences are available?",
    answer: "Each school offers specialized career development support, including internships and clinical placements at domestic and international sites.",
    keywords: ["internships", "clinical experience", "career development", "experiential learning"]
  },
  {
    
    category: "Medical School Financial Aid",
    question: "Do I have to re-apply for financial aid every year?",
    answer: "Yes. Students must re-apply each year. The recommended deadline is March 1. The FAFSA for 2026–27 opens on October 1.",
    keywords: ["reapply", "financial aid", "FAFSA", "deadline"]
  },
  {
    
    category: "Medical School Financial Aid",
    question: "Will I need to report my parents' income and asset information on the FAFSA?",
    answer: "Yes. Parent information is required for institutional aid, even if the applicant is considered independent for federal loans.",
    keywords: ["FAFSA", "parent information", "income", "institutional aid"]
  },
  {
    
    category: "Medical School Financial Aid",
    question: "How do I determine the additional amount I can borrow in a Federal Graduate PLUS or private loan?",
    answer: "You may borrow up to the cost of attendance (COA) minus any other aid received.",
    keywords: ["Graduate PLUS", "private loan", "COA", "borrowing limit"]
  },
  {
    
    category: "Medical School Financial Aid",
    question: "Do I have to accept the full amount of the loan offered?",
    answer: "No. You may accept all or part of the offered loan.",
    keywords: ["loan amount", "accept loan", "financial aid letter"]
  },
  {
    
    category: "Medical School Financial Aid",
    question: "Can I borrow loans for relocation expenses?",
    answer: "No. Relocation expenses are not included in the cost of attendance and must be budgeted personally.",
    keywords: ["relocation", "loan", "COA"]
  },
  {
    
    category: "Medical School Financial Aid",
    question: "Can I get an increase to my cost of attendance if I choose to live alone?",
    answer: "No. The budget assumes at least one roommate and is not increased for living alone.",
    keywords: ["COA", "housing", "living alone"]
  },
  {
    
    category: "Medical School Financial Aid",
    question: "Whom should I contact if I borrowed a Federal Loan as an undergraduate?",
    answer: "You must notify your lender to initiate a loan deferment.",
    keywords: ["loan deferment", "lender", "undergraduate loans"]
  },
  {
    
    category: "Medical School Financial Aid",
    question: "If I have already started a semester, may I still apply for financial aid?",
    answer: "Yes, as long as all paperwork and FAFSA results are complete before the last date of enrollment.",
    keywords: ["apply late", "financial aid", "semester started"]
  },
  {
    
    category: "Medical School Financial Aid",
    question: "How are my Federal Direct Loan funds credited?",
    answer: "Funds disburse no sooner than 10 days before each semester and are applied to the student account.",
    keywords: ["loan disbursement", "Direct Loan"]
  },
  {
    
    category: "Medical School Financial Aid",
    question: "What are my repayment options for Federal Graduate PLUS Loans after graduation?",
    answer: "Payments may be deferred for six months, though interest accrues. Additional options include forbearance.",
    keywords: ["Graduate PLUS", "repayment", "deferment", "forbearance"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "Do I have to re-apply for financial aid every year?",
    answer: "Yes. You must re-apply for financial aid each year. The recommended FAFSA submission deadline is March 15. FAFSA opens on October 1 for the 2026-27 application year.",
    keywords: ["financial aid", "reapply", "FAFSA", "deadline"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "Am I required to attend law school full-time in order to be eligible for financial aid?",
    answer: "Most federal financial aid programs require at least half-time attendance (6 credits). Some scholarships may require full-time enrollment.",
    keywords: ["full-time", "half-time", "financial aid eligibility", "credits"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "I didn’t remember filling out certain forms last year—why do I have to do it this year?",
    answer: "While the FAFSA itself stays the same, additional documentation may be required depending on verification selection, regulations, changes in your financial situation, or inconsistencies. Requirements can vary year to year.",
    keywords: ["forms", "verification", "documentation", "FAFSA"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "What do I do if I borrowed a federal loan as an undergraduate?",
    answer: "You must notify your lender of your return to school to initiate a loan deferment. You may need to complete deferment paperwork and submit it to the registrar’s office.",
    keywords: ["undergraduate loans", "deferment", "lender", "loan repayment"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "How do I determine what additional amount I can borrow in a Graduate PLUS or private education loan?",
    answer: "You may borrow up to the cost of attendance minus any financial aid received. The Office of Financial Aid can help determine remaining eligibility.",
    keywords: ["Graduate PLUS", "private loan", "cost of attendance", "borrowing amount"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "If I have already started a semester, may I still apply for financial aid?",
    answer: "Yes. You can still apply during the semester, but all paperwork must be completed and FAFSA results received before the last date of enrollment.",
    keywords: ["apply late", "semester", "financial aid timeline"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "Do I have to accept the full amount of the loan offered?",
    answer: "No. You may accept all, none, or part of the loan. You can reduce the loan amount before submitting your acceptance.",
    keywords: ["loan acceptance", "reduce loan", "financial award letter"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "Do I need to report my parents’ income on the FAFSA?",
    answer: "No. Law students are considered independent and do not need to report parental information.",
    keywords: ["FAFSA", "independent student", "parent information"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "How are my federal loan funds credited to my account?",
    answer: "Disbursements arrive via electronic transfer in two equal installments and are applied no earlier than the first day of classes. Refunds are issued within 14 days if a credit remains.",
    keywords: ["loan disbursement", "refund", "financial aid process"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "Can I borrow educational loans for relocation expenses?",
    answer: "No. Relocation, car ownership, and summer expenses are not included in the nine-month cost of attendance and must be budgeted using personal resources.",
    keywords: ["relocation expenses", "cost of attendance", "student budget"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "What are my repayment options for Federal PLUS Loans after graduation?",
    answer: "Payments may be deferred for six months, although interest continues to accrue. Additional options such as forbearance must be discussed with the lender.",
    keywords: ["PLUS loan", "repayment", "deferment", "forbearance"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "Can I get an increase to my cost of attendance if I choose to live alone?",
    answer: "No. The budget assumes at least one roommate and is not increased for choosing to live alone.",
    keywords: ["cost of attendance", "housing", "budget increase"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "Can I receive additional financial aid if I take 17 law credits?",
    answer: "If you take more than 15 credits, your COA can be increased to reflect the extra tuition charges, and you may borrow loans for the difference. Scholarships cannot be increased.",
    keywords: ["extra credits", "17 credits", "financial aid increase"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "When will I receive my financial aid award notification?",
    answer: "Entering students receive award notifications beginning in late March. Current students receive theirs in late June after spring grades and class ranks are posted.",
    keywords: ["award notification", "timeline", "financial aid award"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "If I did not receive a merit-based scholarship as a 1L, can I receive one next year?",
    answer: "No. Merit scholarships are only awarded to entering 1L students. Returning students may apply for limited endowed scholarships or outside funding.",
    keywords: ["merit scholarship", "1L", "renewal", "scholarship eligibility"]
  },
  {
    
    category: "Tuition and Financial Aid",
    question: "When can I expect to receive a refund?",
    answer: "Refunds for accounts in credit balance are issued within 14 days of the school receiving funds, either via direct deposit or mailed check.",
    keywords: ["refund", "credit balance", "direct deposit"]
  }

];
module.exports = faqQuestions;

