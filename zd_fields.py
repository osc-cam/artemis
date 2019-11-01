import csv
import re

def replaceMultiple(mainString, toBeReplaces, newString):
    # Iterate over the strings to be replaced
    for elem in toBeReplaces:
        # Check if string is in the main string
        if elem in mainString:
            # Replace the string
            mainString = mainString.replace(elem, newString)
    return mainString

class ZdFields():
    subject = 21909507
    description = 21909517
    status = 21909527
    type = 21909537
    priority = 21909547
    group = 21909557
    assignee = 21909567
    test = 24030857
    manuscript_title = 24069473
    corresponding_author = 24069483
    journal_title = 24069493
    funders = 24069503
    duplicate_of_zd_123456 = 24069513
    wrong_version = 24069523
    publisher = 24069543
    repository_status = 24069553
    doi_like_10_123_abc456 = 24069563
    publication_date = 24069583
    notes = 24069593
    is_there_an_apc_payment = 24071633
    rcuk_policy = 24071783
    coaf_payment = 24071843
    author_department_payment = 24071853
    hefce_exception = 24071863
    hefce_failure = 24071873
    outstanding_commitment_rcuk_inc_vat = 24071913
    apc_invoice_number = 24071953
    green_allowed_version = 24072163
    embargo_duration = 24072173
    corresponding_author_institution = 24114756
    department = 24114766
    acceptance_date = 24114776
    comments_questions = 24114786
    duplicate = 24114796
    repository_link = 24114846
    published = 24114856
    coaf_policy = 24117196
    other_funder_policies = 24117206
    open_access_on_publisher_s_site = 24117216
    is_open_access_obvious = 24117226
    rcuk_payment = 24117246
    other_institution_payment = 24117256
    grant_payment = 24117266
    voucher_membership_offset_payment = 24117276
    retrospective_accepted_pre_april_2016 = 24117286
    no_further_action = 24117296
    externalid = 24117426
    oa_approved_via_prepayment_deal = 24117436
    green_licence = 24117506
    outstanding_commitment_coaf_inc_vat = 24117556
    not_yet_accepted = 24350768
    dspace_done_needs_email = 24522837
    hefce_out_of_scope = 25612958
    wellcome_trust = 26329848
    bloodwise_leukaemia_lymphoma_research = 26329928
    cancer_research_uk = 26352357
    british_heart_foundation = 26352377
    arthritis_research_uk = 26352397
    breast_cancer_now_breast_cancer_campaign = 26352407
    parkinson_s_uk = 28241947
    ahrc = 28673708
    bbsrc = 28673718
    epsrc = 28673728
    mrc = 28673738
    stfc = 28673748
    data_deposition_status = 28676667
    esrc = 28676917
    nerc = 28676927
    in_dark_collection = 29097378
    any_problems_with_the_publisher = 29275238
    what_did_the_publisher_do_wrong = 29275248
    licence_applied_by_publisher = 29275308
    apc_invoice_processed = 29294538
    date_added_to_apollo_yyyy_mm_dd = 29294988
    invoice_date_yyyy_mm_dd = 29295508
    apc_fee_paid_on_cufs = 29312887
    publication_date_yyyy_mm_dd = 29313127
    date_deposit_completed_yyyy_mm_dd = 29313297
    feedback = 29360868
    coaf_grant_numbers = 29867967
    compliance_checking_status = 30105747
    legacy_thesis = 30126358
    hero_thesis = 30126368
    thesis_request_not_digitised = 30126448
    new_thesis = 30145837
    thesis_request_digitised_non_public = 30145857
    edit_existing_repository_record = 30460238
    exception_type = 30491447
    repository_feature_request = 30746518
    dark_collection_status = 31217868
    request_a_copy_action = 33040188
    zd_ticket_number_of_original_submission_zd_123456 = 33053987
    request_a_copy_link = 33085888
    type_of_request = 33185687
    wellcome_supplement_payment = 34261188
    outstanding_commitment_wellcome_supplement = 34288687
    dataset_embargoed = 36226168
    placeholder_dataset = 36226188
    supporting_article_doi = 36336588
    internal_item_id_apollo = 39618567
    sensitive_information = 40424848
    data_supporting_a_publication = 40426148
    accessible_to_peer_reviewers = 40426168
    data_additional_information = 40547127
    promote_on_twitter = 40547167
    twitter_handles = 40547487
    thesis_embargo = 40666587
    symplectic_item_type = 45109748
    no_raw_data_included = 45321107
    rcuk_cost_centre = 46241307
    coaf_cost_centre = 46241967
    dataset_title = 46639347
    crsid = 46829348
    qualification_level = 46829768
    degree_title = 46829788
    thesis_access_level = 46829848
    symplectic_impersonator = 46894327
    external_email_address = 46901347
    awarding_institution = 46901507
    college = 46901527
    degree = 46901887
    thesis_title = 46902187
    thesis_awarded_date = 46903947
    online_publication_date = 47509168
    page_colour_invoice_processed = 48023887
    page_colour_invoice_number = 48023907
    page_colour_invoice_date = 48023927
    page_colour_fee_paid_on_cufs = 48023947
    membership_invoice_processed = 48024147
    membership_invoice_number = 48024167
    membership_invoice_date = 48024187
    membership_fee_paid_on_cufs = 48024347
    impersonator_email_address = 48984068
    online_publication_date_yyyy_mm_dd = 51874167
    apc_invoice_paid = 58141568
    gates_foundation = 61116627
    erc = 71064067
    nihr = 71509888
    fp7 = 73176687
    h2020 = 73663128
    access_exception_type = 76512047
    deposit_exception_type = 76512207
    technical_exception_type = 76949068
    other_exception_type = 76949128
    oasis_type = 77143828
    auto_reply_options = 77351868
    published = 77352028
    hefce_transitional_deadline_met = 77355348
    mrc_core_grant_payment = 79225067
    publication_type = 80501387
    gold_team = 80644248
    apc_already_paid = 80650548
    coaf_failure = 80684087
    deposit_date_date_accessioned_apollo = 80697047
    fast_track_deposit_type = 80793427
    thesis_embargo_reason = 80820127
    corresponding_author_s_affiliation_s = 80911708
    rcuk_failure = 80935588
    rcuk_coaf_failure_action = 81107788
    tweeted = 81113728
    thesis_embargo_reason_other = 81205588
    thesis_deposit_status = 81254948
    thesis_source = 81329868
    thesis_third_party_comments = 114103761454
    thesis_submitted_date = 114103819653
    thesis_ip_comments = 114103819673
    comments_for_theses_team = 114103819693
    wrong_version_type = 360000612693
    nspn_dataset = 360001734153
    sensitive_information_clearance = 360002164833
    university_student_number_usn = 360002164853
    thesis_contains_sensitive_information = 360002184354
    rcuk_funding = 360002184514
    copyright_clearance = 360007648954
    apollo_licence_to_be_deprecated = 360007729673
    apollo_file_versions = 360007729693
    ft_agent = 360007797474
    ft_agent_comments = 360007797494
    sensitive_data_reason = 360007797554
    apc_range = 360008258194
    apollo_licence_tags = 360008530014
    error_during_ft_processing = 360008979714
    gold_licence_options = 360009619733
    apollo_issn = 360009704474
    apollo_eissn = 360009704634
    journal_oa_status = 360012205514
    conference_name = 360014665173
    rac_requester_email = 360014943913
    rac_requester_name = 360014943933
    rac_request_token_link = 360014943953
    rac_all_files_requested = 360014977174
    rac_item_withdrawn = 360014977194
    rac_opt_out = 360014977214
    rac_request_response = 360014977234
    rac_requester_comments = 360015152213
    rac_error_on_file_delivery = 360018970754

    def parse_zd_fieldnames(self, zenexport):
        '''
        Parses csv of custom fields downloaded from Zendesk and outputs a file to facilitate defining this class
        '''
        regex = re.compile(r'\[\w+\]')
        symbols = re.compile(r'[^a-zA-Z0-9_ ]')
        with open('parsed_fieldnames.txt', 'w') as out:
            with open(zenexport) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    field_name = replaceMultiple(row['Title'].lower(),
                                 [' ', '?', '#', '(', ')', "'", '&',
                                  '[', ']', '/', '£', '.', '-', '___', '__'], '_').strip('_')
                    field_id = row['Field ID']
                    out_str = "    {} = {}\n".format(field_name, field_id)
                    out.write(out_str)

if __name__ == "__main__":
    fields = ZdFields()
    fields.parse_zd_fieldnames('camacuk_ticket-fields.csv')



